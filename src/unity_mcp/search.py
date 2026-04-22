"""Search & retrieval over the indexed documentation.

Two clearly-separated paths:
- search_api()    -> precise symbol/class/member lookup (api_records + api_fts)
- search_guides() -> conceptual / how-to lookup        (guide_records + guide_fts)

answer_question() runs both and labels every result so the caller can tell
where each hit came from.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Optional

from .config import DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT
from .db import get_connection
from .models import GuideReference, SearchResult, SymbolReference


# ---------------------------------------------------------------------------
# Query sanitization
# ---------------------------------------------------------------------------

# Tokens FTS5 treats as operators/structure; stripped from caller input so we
# never have to worry about a stray quote crashing a parse.
_FTS_RESERVED = re.compile(r'[\"\(\)\*\:\^]')


def _fts_terms(query: str) -> list[str]:
    """Split a free-form query into FTS-safe terms."""
    cleaned = _FTS_RESERVED.sub(" ", query).strip()
    return [t for t in re.split(r"\s+", cleaned) if t]


def _fts_phrase(query: str) -> str:
    """Wrap the query as a single quoted phrase for exact-phrase MATCH."""
    safe = query.replace('"', '""').strip()
    return f'"{safe}"'


def _fts_or(terms: list[str]) -> str:
    """Build an `a OR b OR c` MATCH expression with prefix tolerance."""
    return " OR ".join(f"{t}*" for t in terms)


# ---------------------------------------------------------------------------
# API search
# ---------------------------------------------------------------------------

# Field weights for bm25 — must match the api_fts column order:
# (symbol_name, title, class_name, namespace, signature, summary, remarks, content_text)
# Lower bm25 score = better match in SQLite's implementation, and a higher
# weight makes a column contribute MORE to relevance, so symbol/title get the
# strongest weights here.
_API_BM25_WEIGHTS = "10.0, 8.0, 5.0, 3.0, 2.0, 1.5, 1.0, 0.5"


def search_api(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    member_type: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[SearchResult]:
    """Precise API/symbol search.

    Order of preference:
      1. Exact symbol_name / title / class_name match (case-insensitive)
      2. symbol_name LIKE "%.<query>" — handles bare member names
      3. FTS5 phrase match weighted toward symbol/title fields
      4. FTS5 prefix-OR fallback for multi-word queries
    """
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    conn = get_connection(db_path, readonly=True)
    try:
        results: list[SearchResult] = []
        seen: set[int] = set()

        type_clause = " AND member_type = ? " if member_type else ""
        type_args: tuple = (member_type,) if member_type else ()

        # 1. Exact matches
        rows = conn.execute(
            f"""
            SELECT id, title, relative_path, symbol_name, class_name, namespace, member_type
            FROM api_records
            WHERE (symbol_name = ?1 COLLATE NOCASE
                OR title       = ?1 COLLATE NOCASE
                OR class_name  = ?1 COLLATE NOCASE)
            {type_clause}
            LIMIT ?
            """,
            (query, *type_args, limit),
        ).fetchall()
        for row in rows:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            results.append(_api_row_to_result(row, snippet=row["symbol_name"] or row["title"], score=-1000.0))

        # 2. Bare member name (e.g. "Rotate" -> "Transform.Rotate")
        if len(results) < limit and "." not in query:
            rows = conn.execute(
                f"""
                SELECT id, title, relative_path, symbol_name, class_name, namespace, member_type
                FROM api_records
                WHERE symbol_name LIKE ? COLLATE NOCASE {type_clause}
                LIMIT ?
                """,
                (f"%.{query}", *type_args, limit - len(results)),
            ).fetchall()
            for row in rows:
                if row["id"] in seen:
                    continue
                seen.add(row["id"])
                results.append(_api_row_to_result(row, snippet=row["symbol_name"], score=-500.0))

        # 3 & 4. FTS5 ranked search
        if len(results) < limit:
            terms = _fts_terms(query)
            if terms:
                fts_results = _fts_api(conn, _fts_phrase(query), member_type, limit)
                if not fts_results:
                    fts_results = _fts_api(conn, _fts_or(terms), member_type, limit)
                for r in fts_results:
                    if r.id in seen:
                        continue
                    seen.add(r.id)
                    results.append(r)

        return results[:limit]
    finally:
        conn.close()


def _fts_api(
    conn: sqlite3.Connection,
    match_expr: str,
    member_type: Optional[str],
    limit: int,
) -> list[SearchResult]:
    type_clause = " AND r.member_type = ? " if member_type else ""
    type_args: tuple = (member_type,) if member_type else ()
    sql = f"""
        SELECT
            r.id, r.title, r.relative_path, r.symbol_name, r.class_name,
            r.namespace, r.member_type,
            snippet(api_fts, 7, '>>', '<<', '...', 18) AS snippet,
            bm25(api_fts, {_API_BM25_WEIGHTS}) AS score
        FROM api_fts
        JOIN api_records r ON r.id = api_fts.rowid
        WHERE api_fts MATCH ? {type_clause}
        ORDER BY score
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, (match_expr, *type_args, limit)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [_api_row_to_result(row, snippet=row["snippet"], score=row["score"]) for row in rows]


def _api_row_to_result(row: sqlite3.Row, snippet: str, score: float) -> SearchResult:
    return SearchResult(
        id=row["id"],
        category="api",
        title=row["title"],
        relative_path=row["relative_path"],
        snippet=(snippet or "")[:500],
        score=score,
        symbol_name=row["symbol_name"] or "",
        class_name=row["class_name"] or "",
        namespace=row["namespace"] or "",
        member_type=row["member_type"] or "",
    )


# ---------------------------------------------------------------------------
# Guide search
# ---------------------------------------------------------------------------

# guide_fts columns: (title, key_topics, summary, content_text)
# Title and headings carry the strongest concept signal; prose is least precise.
_GUIDE_BM25_WEIGHTS = "8.0, 5.0, 3.0, 1.0"


def search_guides(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    guide_type: Optional[str] = None,
    db_path: Optional[Path] = None,
) -> list[SearchResult]:
    """Conceptual / how-to search.

    Strategy:
      - FTS5 phrase match first (best precision).
      - Fall back to prefix-OR over the cleaned terms for natural-language queries.
      - Boost any title-substring match over pure FTS hits.
    """
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    conn = get_connection(db_path, readonly=True)
    try:
        results: list[SearchResult] = []
        seen: set[int] = set()

        type_clause = " AND r.guide_type = ? " if guide_type else ""
        type_args: tuple = (guide_type,) if guide_type else ()

        # Title substring boost — cheap and very effective for "how to X" queries.
        rows = conn.execute(
            f"""
            SELECT id, title, relative_path, guide_type, summary
            FROM guide_records r
            WHERE title LIKE ? COLLATE NOCASE {type_clause}
            LIMIT ?
            """,
            (f"%{query}%", *type_args, limit),
        ).fetchall()
        for row in rows:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            results.append(_guide_row_to_result(
                row, snippet=row["summary"] or row["title"], score=-100.0,
            ))

        if len(results) < limit:
            terms = _fts_terms(query)
            if terms:
                fts_hits = _fts_guides(conn, _fts_phrase(query), guide_type, limit)
                if not fts_hits:
                    fts_hits = _fts_guides(conn, _fts_or(terms), guide_type, limit)
                for r in fts_hits:
                    if r.id in seen:
                        continue
                    seen.add(r.id)
                    results.append(r)

        return results[:limit]
    finally:
        conn.close()


def _fts_guides(
    conn: sqlite3.Connection,
    match_expr: str,
    guide_type: Optional[str],
    limit: int,
) -> list[SearchResult]:
    type_clause = " AND r.guide_type = ? " if guide_type else ""
    type_args: tuple = (guide_type,) if guide_type else ()
    sql = f"""
        SELECT
            r.id, r.title, r.relative_path, r.guide_type, r.summary,
            snippet(guide_fts, 3, '>>', '<<', '...', 22) AS snippet,
            bm25(guide_fts, {_GUIDE_BM25_WEIGHTS}) AS score
        FROM guide_fts
        JOIN guide_records r ON r.id = guide_fts.rowid
        WHERE guide_fts MATCH ? {type_clause}
        ORDER BY score
        LIMIT ?
    """
    try:
        rows = conn.execute(sql, (match_expr, *type_args, limit)).fetchall()
    except sqlite3.OperationalError:
        return []
    return [_guide_row_to_result(row, snippet=row["snippet"], score=row["score"]) for row in rows]


def _guide_row_to_result(row: sqlite3.Row, snippet: str, score: float) -> SearchResult:
    return SearchResult(
        id=row["id"],
        category="guide",
        title=row["title"],
        relative_path=row["relative_path"],
        snippet=(snippet or "")[:500],
        score=score,
        guide_type=row["guide_type"] if "guide_type" in row.keys() else "",
    )


# ---------------------------------------------------------------------------
# Combined "answer a question" path
# ---------------------------------------------------------------------------

def answer_question(
    query: str,
    limit_per_index: int = 5,
    db_path: Optional[Path] = None,
) -> dict[str, list[SearchResult]]:
    """Run both indexes, return a labeled bundle.

    Caller (or LLM) can decide whether the question is API-precise or
    conceptual based on which side returned the strongest matches.
    """
    limit_per_index = max(1, min(limit_per_index, MAX_SEARCH_LIMIT))
    return {
        "api": search_api(query, limit=limit_per_index, db_path=db_path),
        "guide": search_guides(query, limit=limit_per_index, db_path=db_path),
    }


# ---------------------------------------------------------------------------
# Symbol lookup (API only)
# ---------------------------------------------------------------------------

def get_symbol_reference(
    symbol: str,
    db_path: Optional[Path] = None,
) -> Optional[SymbolReference]:
    """Look up a single API symbol with structured fields."""
    conn = get_connection(db_path, readonly=True)
    try:
        # 1. Exact symbol_name (Transform.Rotate)
        row = conn.execute(
            "SELECT * FROM api_records WHERE symbol_name = ? COLLATE NOCASE LIMIT 1",
            (symbol,),
        ).fetchone()

        # 2. Exact title
        if not row:
            row = conn.execute(
                "SELECT * FROM api_records WHERE title = ? COLLATE NOCASE LIMIT 1",
                (symbol,),
            ).fetchone()

        # 3. Bare member name
        if not row and "." not in symbol:
            row = conn.execute(
                "SELECT * FROM api_records WHERE symbol_name LIKE ? COLLATE NOCASE LIMIT 1",
                (f"%.{symbol}",),
            ).fetchone()

        # 4. Exact class
        if not row:
            row = conn.execute(
                "SELECT * FROM api_records WHERE class_name = ? COLLATE NOCASE LIMIT 1",
                (symbol,),
            ).fetchone()

        # 5. FTS over symbol-weighted columns
        if not row:
            try:
                row = conn.execute(
                    f"""
                    SELECT r.* FROM api_fts
                    JOIN api_records r ON r.id = api_fts.rowid
                    WHERE api_fts MATCH ?
                    ORDER BY bm25(api_fts, {_API_BM25_WEIGHTS})
                    LIMIT 1
                    """,
                    (_fts_phrase(symbol),),
                ).fetchone()
            except sqlite3.OperationalError:
                row = None

        return SymbolReference.from_row(dict(row)) if row else None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Page lookup (either category)
# ---------------------------------------------------------------------------

def get_doc_page(
    path_or_key: str,
    db_path: Optional[Path] = None,
) -> Optional[dict]:
    """Retrieve a doc page by path/substring from either index.

    Returns a dict: {"category": "api"|"guide", "ref": <SymbolReference|GuideReference>}.
    Tries the API table first (ScriptReference paths are more specific); on miss,
    falls back to guides.
    """
    conn = get_connection(db_path, readonly=True)
    try:
        for category, table, builder in (
            ("api", "api_records", SymbolReference.from_row),
            ("guide", "guide_records", GuideReference.from_row),
        ):
            row = conn.execute(
                f"""
                SELECT * FROM {table}
                WHERE relative_path = ? COLLATE NOCASE
                   OR relative_path LIKE ? COLLATE NOCASE
                ORDER BY length(relative_path)
                LIMIT 1
                """,
                (path_or_key, f"%{path_or_key}%"),
            ).fetchone()
            if row:
                return {"category": category, "ref": builder(dict(row))}
        return None
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def get_stats(db_path: Optional[Path] = None) -> dict:
    conn = get_connection(db_path, readonly=True)
    try:
        api_total = conn.execute("SELECT COUNT(*) FROM api_records").fetchone()[0]
        guide_total = conn.execute("SELECT COUNT(*) FROM guide_records").fetchone()[0]
        unique_classes = conn.execute(
            "SELECT COUNT(DISTINCT class_name) FROM api_records WHERE class_name != ''"
        ).fetchone()[0]
        unique_namespaces = conn.execute(
            "SELECT COUNT(DISTINCT namespace) FROM api_records WHERE namespace != ''"
        ).fetchone()[0]
        guide_breakdown = {
            row["guide_type"]: row["c"]
            for row in conn.execute(
                "SELECT guide_type, COUNT(*) AS c FROM guide_records GROUP BY guide_type"
            ).fetchall()
        }
        member_breakdown = {
            row["member_type"]: row["c"]
            for row in conn.execute(
                "SELECT member_type, COUNT(*) AS c FROM api_records GROUP BY member_type"
            ).fetchall()
        }
        return {
            "api_pages": api_total,
            "guide_pages": guide_total,
            "total_pages": api_total + guide_total,
            "unique_classes": unique_classes,
            "unique_namespaces": unique_namespaces,
            "guide_breakdown": guide_breakdown,
            "api_member_breakdown": member_breakdown,
        }
    finally:
        conn.close()
