"""Search and retrieval over one or more indexed docsets."""

from __future__ import annotations

import re
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Optional

from .config import DEFAULT_SEARCH_LIMIT, MAX_SEARCH_LIMIT
from .db import get_connection
from .docsets import DocsetSpec, select_docsets
from .models import GuideReference, SearchResult, SymbolReference


class IndexNotReadyError(RuntimeError):
    """Raised when a selected docset exists but has not been indexed yet."""


_FTS_RESERVED = re.compile(r'[\"\(\)\*\:\^]')

# api_fts columns:
# (symbol_name, title, class_name, namespace, module_name, topic_path,
#  signature, summary, remarks, content_text)
_API_BM25_WEIGHTS = "12.0, 9.0, 6.0, 3.0, 5.0, 3.0, 2.0, 1.5, 1.0, 0.5"

# guide_fts columns: (title, topic_path, key_topics, summary, content_text)
_GUIDE_BM25_WEIGHTS = "8.0, 4.0, 5.0, 3.0, 1.0"


def _fts_terms(query: str) -> list[str]:
    cleaned = _FTS_RESERVED.sub(" ", query).strip()
    return [term for term in re.split(r"\s+", cleaned) if term]


def _fts_phrase(query: str) -> str:
    safe = query.replace('"', '""').strip()
    return f'"{safe}"'


def _fts_or(terms: list[str]) -> str:
    return " OR ".join(f"{term}*" for term in terms)


def _resolve_indexed_docsets(
    *,
    engine: str | None,
    version: str | None,
    docset: str | None,
) -> list[DocsetSpec]:
    specs = select_docsets(
        engine=engine,
        version=version,
        docset=docset,
    )
    if not specs:
        raise ValueError("No matching documentation targets were found.")

    indexed = [spec for spec in specs if spec.indexed]
    if indexed:
        return indexed

    labels = ", ".join(spec.key for spec in specs)
    raise IndexNotReadyError(
        f"No index database is available for the selected docset(s): {labels}. "
        "Build the index first with scripts/build_index.py."
    )


def _api_row_to_result(
    row: sqlite3.Row,
    snippet: str,
    score: float,
    spec: DocsetSpec,
) -> SearchResult:
    return SearchResult(
        id=row["id"],
        category="api",
        title=row["title"],
        relative_path=row["relative_path"],
        snippet=(snippet or "")[:500],
        score=score,
        engine=spec.engine,
        version=spec.version,
        docset=spec.docset,
        docset_label=spec.label,
        symbol_name=row["symbol_name"] or "",
        class_name=row["class_name"] or "",
        namespace=row["namespace"] or "",
        member_type=row["member_type"] or "",
        module_name=row["module_name"] or "",
        topic_path=row["topic_path"] or "",
    )


def _guide_row_to_result(
    row: sqlite3.Row,
    snippet: str,
    score: float,
    spec: DocsetSpec,
) -> SearchResult:
    return SearchResult(
        id=row["id"],
        category="guide",
        title=row["title"],
        relative_path=row["relative_path"],
        snippet=(snippet or "")[:500],
        score=score,
        engine=spec.engine,
        version=spec.version,
        docset=spec.docset,
        docset_label=spec.label,
        guide_type=row["guide_type"] if "guide_type" in row.keys() else "",
        topic_path=row["topic_path"] if "topic_path" in row.keys() else "",
    )


def _search_api_single_docset(
    query: str,
    spec: DocsetSpec,
    *,
    limit: int,
    member_type: Optional[str] = None,
) -> list[SearchResult]:
    conn = get_connection(spec.db_path, readonly=True)
    try:
        results: list[SearchResult] = []
        seen: set[int] = set()

        type_clause = " AND member_type = ? " if member_type else ""
        type_args: tuple = (member_type,) if member_type else ()

        rows = conn.execute(
            f"""
            SELECT id, title, relative_path, symbol_name, class_name, namespace,
                   module_name, topic_path, member_type
            FROM api_records
            WHERE (
                    symbol_name = ?1 COLLATE NOCASE
                OR  title       = ?1 COLLATE NOCASE
                OR  class_name  = ?1 COLLATE NOCASE
                OR  module_name = ?1 COLLATE NOCASE
            )
            {type_clause}
            LIMIT ?
            """,
            (query, *type_args, limit),
        ).fetchall()
        for row in rows:
            if row["id"] in seen:
                continue
            seen.add(row["id"])
            results.append(
                _api_row_to_result(
                    row,
                    snippet=row["symbol_name"] or row["title"],
                    score=-1000.0,
                    spec=spec,
                )
            )

        if len(results) < limit and "." not in query and "::" not in query:
            rows = conn.execute(
                f"""
                SELECT id, title, relative_path, symbol_name, class_name, namespace,
                       module_name, topic_path, member_type
                FROM api_records
                WHERE (
                        symbol_name LIKE ? COLLATE NOCASE
                    OR  title LIKE ? COLLATE NOCASE
                )
                {type_clause}
                LIMIT ?
                """,
                (f"%.{query}", f"%::{query}", *type_args, limit - len(results)),
            ).fetchall()
            for row in rows:
                if row["id"] in seen:
                    continue
                seen.add(row["id"])
                results.append(_api_row_to_result(row, row["symbol_name"], -500.0, spec))

        if len(results) < limit:
            terms = _fts_terms(query)
            if terms:
                fts_hits = _fts_api(conn, spec, _fts_phrase(query), member_type, limit)
                if not fts_hits:
                    fts_hits = _fts_api(conn, spec, _fts_or(terms), member_type, limit)
                for result in fts_hits:
                    if result.id in seen:
                        continue
                    seen.add(result.id)
                    results.append(result)

        return results[:limit]
    finally:
        conn.close()


def _fts_api(
    conn: sqlite3.Connection,
    spec: DocsetSpec,
    match_expr: str,
    member_type: Optional[str],
    limit: int,
) -> list[SearchResult]:
    type_clause = " AND r.member_type = ? " if member_type else ""
    type_args: tuple = (member_type,) if member_type else ()
    sql = f"""
        SELECT
            r.id, r.title, r.relative_path, r.symbol_name, r.class_name,
            r.namespace, r.module_name, r.topic_path, r.member_type,
            snippet(api_fts, 9, '>>', '<<', '...', 18) AS snippet,
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
    return [_api_row_to_result(row, row["snippet"], row["score"], spec) for row in rows]


def _search_guides_single_docset(
    query: str,
    spec: DocsetSpec,
    *,
    limit: int,
    guide_type: Optional[str] = None,
) -> list[SearchResult]:
    conn = get_connection(spec.db_path, readonly=True)
    try:
        results: list[SearchResult] = []
        seen: set[int] = set()

        type_clause = " AND r.guide_type = ? " if guide_type else ""
        type_args: tuple = (guide_type,) if guide_type else ()

        rows = conn.execute(
            f"""
            SELECT id, title, relative_path, guide_type, topic_path, summary
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
            results.append(_guide_row_to_result(row, row["summary"] or row["title"], -100.0, spec))

        if len(results) < limit:
            terms = _fts_terms(query)
            if terms:
                fts_hits = _fts_guides(conn, spec, _fts_phrase(query), guide_type, limit)
                if not fts_hits:
                    fts_hits = _fts_guides(conn, spec, _fts_or(terms), guide_type, limit)
                for result in fts_hits:
                    if result.id in seen:
                        continue
                    seen.add(result.id)
                    results.append(result)

        return results[:limit]
    finally:
        conn.close()


def _fts_guides(
    conn: sqlite3.Connection,
    spec: DocsetSpec,
    match_expr: str,
    guide_type: Optional[str],
    limit: int,
) -> list[SearchResult]:
    type_clause = " AND r.guide_type = ? " if guide_type else ""
    type_args: tuple = (guide_type,) if guide_type else ()
    sql = f"""
        SELECT
            r.id, r.title, r.relative_path, r.guide_type, r.topic_path, r.summary,
            snippet(guide_fts, 4, '>>', '<<', '...', 22) AS snippet,
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
    return [_guide_row_to_result(row, row["snippet"], row["score"], spec) for row in rows]


def search_api(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    member_type: Optional[str] = None,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> list[SearchResult]:
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    specs = _resolve_indexed_docsets(engine=engine, version=version, docset=docset)

    results: list[SearchResult] = []
    per_docset_limit = max(limit, 10)
    for spec in specs:
        results.extend(
            _search_api_single_docset(query, spec, limit=per_docset_limit, member_type=member_type)
        )
    results.sort(key=lambda item: (item.score, item.title.lower(), item.relative_path.lower()))
    return results[:limit]


def search_guides(
    query: str,
    limit: int = DEFAULT_SEARCH_LIMIT,
    guide_type: Optional[str] = None,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> list[SearchResult]:
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    specs = _resolve_indexed_docsets(engine=engine, version=version, docset=docset)

    results: list[SearchResult] = []
    per_docset_limit = max(limit, 10)
    for spec in specs:
        results.extend(
            _search_guides_single_docset(query, spec, limit=per_docset_limit, guide_type=guide_type)
        )
    results.sort(key=lambda item: (item.score, item.title.lower(), item.relative_path.lower()))
    return results[:limit]


def answer_question(
    query: str,
    limit_per_index: int = 5,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> dict[str, list[SearchResult]]:
    limit_per_index = max(1, min(limit_per_index, MAX_SEARCH_LIMIT))
    return {
        "api": search_api(query, limit=limit_per_index, engine=engine, version=version, docset=docset),
        "guide": search_guides(
            query,
            limit=limit_per_index,
            engine=engine,
            version=version,
            docset=docset,
        ),
    }


def _symbol_reference_single(
    symbol: str,
    spec: DocsetSpec,
) -> tuple[int, SymbolReference] | None:
    conn = get_connection(spec.db_path, readonly=True)
    try:
        row = conn.execute(
            "SELECT * FROM api_records WHERE symbol_name = ? COLLATE NOCASE LIMIT 1",
            (symbol,),
        ).fetchone()
        rank = 0

        if not row:
            row = conn.execute(
                "SELECT * FROM api_records WHERE title = ? COLLATE NOCASE LIMIT 1",
                (symbol,),
            ).fetchone()
            rank = 1

        if not row and "." not in symbol and "::" not in symbol:
            row = conn.execute(
                """
                SELECT * FROM api_records
                WHERE symbol_name LIKE ? COLLATE NOCASE
                   OR title LIKE ? COLLATE NOCASE
                LIMIT 1
                """,
                (f"%.{symbol}", f"%::{symbol}"),
            ).fetchone()
            rank = 2

        if not row:
            row = conn.execute(
                "SELECT * FROM api_records WHERE class_name = ? COLLATE NOCASE LIMIT 1",
                (symbol,),
            ).fetchone()
            rank = 3

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
                rank = 4
            except sqlite3.OperationalError:
                row = None

        if not row:
            return None

        return (
            rank,
            SymbolReference.from_row(
                dict(row),
                engine=spec.engine,
                version=spec.version,
                docset=spec.docset,
                docset_label=spec.label,
            ),
        )
    finally:
        conn.close()


def get_symbol_reference(
    symbol: str,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> Optional[SymbolReference]:
    specs = _resolve_indexed_docsets(engine=engine, version=version, docset=docset)
    candidates: list[tuple[int, SymbolReference]] = []
    for spec in specs:
        hit = _symbol_reference_single(symbol, spec)
        if hit:
            candidates.append(hit)
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            item[0],
            len(item[1].relative_path),
            item[1].docset_label.lower(),
            item[1].title.lower(),
        )
    )
    return candidates[0][1]


def _doc_page_single(path_or_key: str, spec: DocsetSpec) -> tuple[int, dict] | None:
    conn = get_connection(spec.db_path, readonly=True)
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
                ORDER BY
                    CASE WHEN relative_path = ? COLLATE NOCASE THEN 0 ELSE 1 END,
                    length(relative_path)
                LIMIT 1
                """,
                (path_or_key, f"%{path_or_key}%", path_or_key),
            ).fetchone()
            if not row:
                continue
            ref = builder(
                dict(row),
                engine=spec.engine,
                version=spec.version,
                docset=spec.docset,
                docset_label=spec.label,
            )
            priority = 0 if row["relative_path"].lower() == path_or_key.lower() else 1
            return priority, {"category": category, "ref": ref}
        return None
    finally:
        conn.close()


def get_doc_page(
    path_or_key: str,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> Optional[dict]:
    specs = _resolve_indexed_docsets(engine=engine, version=version, docset=docset)
    candidates: list[tuple[int, dict]] = []
    for spec in specs:
        hit = _doc_page_single(path_or_key, spec)
        if hit:
            candidates.append(hit)
    if not candidates:
        return None
    candidates.sort(
        key=lambda item: (
            item[0],
            len(item[1]["ref"].relative_path),
            item[1]["ref"].docset_label.lower(),
        )
    )
    return candidates[0][1]


def get_stats(
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> dict:
    specs = _resolve_indexed_docsets(
        engine=engine,
        version=version,
        docset=docset,
    )

    api_total = 0
    guide_total = 0
    unique_classes: set[str] = set()
    unique_namespaces: set[str] = set()
    guide_breakdown: Counter[str] = Counter()
    member_breakdown: Counter[str] = Counter()
    docset_rows: list[dict[str, object]] = []

    for spec in specs:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            api_pages = conn.execute("SELECT COUNT(*) FROM api_records").fetchone()[0]
            guide_pages = conn.execute("SELECT COUNT(*) FROM guide_records").fetchone()[0]
            api_total += api_pages
            guide_total += guide_pages

            unique_classes.update(
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT class_name FROM api_records WHERE class_name != ''"
                ).fetchall()
            )
            unique_namespaces.update(
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT namespace FROM api_records WHERE namespace != ''"
                ).fetchall()
            )
            member_breakdown.update(
                {
                    row["member_type"]: row["c"]
                    for row in conn.execute(
                        "SELECT member_type, COUNT(*) AS c FROM api_records GROUP BY member_type"
                    ).fetchall()
                }
            )
            guide_breakdown.update(
                {
                    row["guide_type"]: row["c"]
                    for row in conn.execute(
                        "SELECT guide_type, COUNT(*) AS c FROM guide_records GROUP BY guide_type"
                    ).fetchall()
                }
            )
            docset_rows.append(
                {
                    "key": spec.key,
                    "label": spec.label,
                    "engine": spec.engine,
                    "version": spec.version,
                    "docset": spec.docset,
                    "api_pages": api_pages,
                    "guide_pages": guide_pages,
                    "docs_root": str(spec.docs_root),
                    "db_path": str(spec.db_path),
                }
            )
        finally:
            conn.close()

    return {
        "docsets": docset_rows,
        "api_pages": api_total,
        "guide_pages": guide_total,
        "total_pages": api_total + guide_total,
        "unique_classes": len(unique_classes),
        "unique_namespaces": len(unique_namespaces),
        "guide_breakdown": dict(guide_breakdown),
        "api_member_breakdown": dict(member_breakdown),
    }
