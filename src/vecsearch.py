"""Vector search over indexed docsets using LanceDB + hybrid RRF fusion.

Architecture
------------
* Each docset gets its own LanceDB table stored under ``DATA_DIR/vectors/``.
* During indexing, API and guide records are embedded and upserted into
  LanceDB alongside their row id and category.
* At query time the caller can choose:

  - **keyword** – pure FTS5 (existing :class:`DocSearcher`).
  - **semantic** – pure vector similarity via LanceDB.
  - **hybrid** (default) – Reciprocal Rank Fusion of both result sets.

The public entry points are:

* :func:`semantic_search` – vector-only search across docsets.
* :func:`hybrid_search` – FTS5 + vector RRF fusion.
* :func:`build_vector_index` – embed and store vectors for one docset.
"""

from __future__ import annotations

import logging
from pathlib import Path


from .config import (
    DEFAULT_SEARCH_LIMIT,
    MAX_SEARCH_LIMIT,
    VECTOR_DB_DIR,
)
from .docsets import DocsetSpec, select_docsets
from .embedding import EmbeddingModel, get_embedding_model
from .models import SearchResult
from .search import (
    IndexNotReadyError,
)
from .db import get_connection

logger = logging.getLogger(__name__)

# RRF constant (standard value from the original paper)
_RRF_K = 60


# ---------------------------------------------------------------------------
# Row mappers (same logic as search.py but kept local to avoid coupling)
# ---------------------------------------------------------------------------


def _api_row_to_result(
    row, snippet: str, score: float, spec: DocsetSpec
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
    row, snippet: str, score: float, spec: DocsetSpec
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


# ---------------------------------------------------------------------------
# LanceDB helpers
# ---------------------------------------------------------------------------


def _vec_db_path() -> Path:
    VECTOR_DB_DIR.mkdir(parents=True, exist_ok=True)
    return VECTOR_DB_DIR


def _table_name(spec: DocsetSpec) -> str:
    return spec.key.replace(":", "__").replace(".", "_")


def _open_table(spec: DocsetSpec):
    """Open (or create) the LanceDB table for *spec*.  Returns ``(db, table_or_None)``."""
    import lancedb

    db = lancedb.connect(str(_vec_db_path()))
    name = _table_name(spec)
    try:
        return db, db.open_table(name)
    except Exception:
        return db, None


def _record_exists(spec: DocsetSpec) -> bool:
    """Check if a vector table already exists for *spec*."""
    import lancedb

    db = lancedb.connect(str(_vec_db_path()))
    name = _table_name(spec)
    try:
        db.open_table(name)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Vector index building
# ---------------------------------------------------------------------------


def build_vector_index(
    spec: DocsetSpec,
    model: EmbeddingModel | None = None,
    *,
    batch_size: int = 128,
    force: bool = False,
) -> dict:
    """Embed all records for *spec* and store them in LanceDB.

    Returns a stats dict with keys ``api_embedded``, ``guide_embedded``,
    ``elapsed_seconds``.
    """
    import lancedb
    import time

    if not spec.indexed:
        raise IndexNotReadyError(f"No SQLite index for {spec.key}")

    model = model or get_embedding_model()
    start = time.time()

    db = lancedb.connect(str(_vec_db_path()))
    name = _table_name(spec)

    conn = get_connection(spec.db_path, readonly=True)
    try:
        records = []

        # Embed API records
        api_rows = conn.execute(
            "SELECT id, symbol_name, title, class_name, summary, content_text FROM api_records"
        ).fetchall()
        api_texts = []
        api_ids = []
        for row in api_rows:
            text = " ".join(
                filter(
                    None,
                    [
                        row["symbol_name"],
                        row["title"],
                        row["class_name"],
                        row["summary"],
                        row["content_text"][:500],
                    ],
                )
            )
            api_texts.append(text)
            api_ids.append(row["id"])

        api_embedded = 0
        for i in range(0, len(api_texts), batch_size):
            batch_texts = api_texts[i : i + batch_size]
            batch_ids = api_ids[i : i + batch_size]
            embeddings = model.encode(batch_texts)
            for j, (rid, emb) in enumerate(zip(batch_ids, embeddings)):
                records.append(
                    {
                        "rowid": rid,
                        "category": "api",
                        "text": batch_texts[j][:200],
                        "vector": emb.tolist(),
                    }
                )
            api_embedded += len(batch_texts)

        # Embed guide records
        guide_rows = conn.execute(
            "SELECT id, title, summary, content_text FROM guide_records"
        ).fetchall()
        guide_texts = []
        guide_ids = []
        for row in guide_rows:
            text = " ".join(
                filter(
                    None,
                    [
                        row["title"],
                        row["summary"],
                        row["content_text"][:500],
                    ],
                )
            )
            guide_texts.append(text)
            guide_ids.append(row["id"])

        guide_embedded = 0
        for i in range(0, len(guide_texts), batch_size):
            batch_texts = guide_texts[i : i + batch_size]
            batch_ids = guide_ids[i : i + batch_size]
            embeddings = model.encode(batch_texts)
            for j, (rid, emb) in enumerate(zip(batch_ids, embeddings)):
                records.append(
                    {
                        "rowid": rid,
                        "category": "guide",
                        "text": batch_texts[j][:200],
                        "vector": emb.tolist(),
                    }
                )
            guide_embedded += len(batch_texts)

        if records:
            db.create_table(name, records, mode="overwrite")
        elif not force:
            logger.info("No records to embed for %s", spec.key)

    finally:
        conn.close()

    elapsed = time.time() - start
    return {
        "engine": spec.engine,
        "version": spec.version,
        "docset": spec.docset,
        "api_embedded": api_embedded,
        "guide_embedded": guide_embedded,
        "elapsed_seconds": round(elapsed, 2),
    }


# ---------------------------------------------------------------------------
# Vector search
# ---------------------------------------------------------------------------


def vector_search_single(
    query: str,
    spec: DocsetSpec,
    *,
    limit: int = DEFAULT_SEARCH_LIMIT,
    category: str | None = None,
) -> list[tuple[int, float]]:
    """Run a vector similarity search in one docset.

    Returns a list of ``(sqlite_rowid, distance)`` tuples.
    """
    import lancedb

    model = get_embedding_model()
    query_vec = model.encode_single(query).tolist()

    db = lancedb.connect(str(_vec_db_path()))
    name = _table_name(spec)

    try:
        table = db.open_table(name)
    except Exception:
        return []

    search = table.search(query_vec).limit(limit)
    if category:
        search = search.where(f"category = '{category}'")
    results = search.to_list()
    return [(r["rowid"], r["_distance"]) for r in results]


def vector_search(
    query: str,
    *,
    limit: int = DEFAULT_SEARCH_LIMIT,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    category: str | None = None,
) -> list[SearchResult]:
    """Pure vector similarity search across matching docsets."""
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    specs = _resolve_specs(engine=engine, version=version, docset=docset)

    results: list[SearchResult] = []
    for spec in specs:
        hits = vector_search_single(query, spec, limit=limit, category=category)
        if not hits:
            continue

        conn = get_connection(spec.db_path, readonly=True)
        try:
            for rowid, distance in hits:
                row = conn.execute(
                    "SELECT * FROM api_records WHERE id = ?", (rowid,)
                ).fetchone()
                if row:
                    results.append(
                        _api_row_to_result(
                            row,
                            row["summary"] or row["symbol_name"] or row["title"],
                            distance,
                            spec,
                        )
                    )
                    continue
                row = conn.execute(
                    "SELECT * FROM guide_records WHERE id = ?", (rowid,)
                ).fetchone()
                if row:
                    results.append(
                        _guide_row_to_result(
                            row,
                            row["summary"] or row["title"],
                            distance,
                            spec,
                        )
                    )
        finally:
            conn.close()

    results.sort(key=lambda r: r.score)
    return results[:limit]


# ---------------------------------------------------------------------------
# Hybrid search with Reciprocal Rank Fusion
# ---------------------------------------------------------------------------


def _rrf_merge(
    keyword_results: list[SearchResult],
    vector_results: list[SearchResult],
    k: int = _RRF_K,
) -> list[SearchResult]:
    """Merge two ranked lists using Reciprocal Rank Fusion.

    Each result is scored as ``sum(1 / (k + rank))`` across both lists.
    Ties are broken by original score, then title.
    """
    scores: dict[tuple[str, int], float] = {}
    meta: dict[tuple[str, int], SearchResult] = {}

    for rank, r in enumerate(keyword_results, 1):
        key = (r.category, r.id)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        meta[key] = r

    for rank, r in enumerate(vector_results, 1):
        key = (r.category, r.id)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
        meta[key] = r

    sorted_keys = sorted(
        scores.keys(),
        key=lambda ky: (-scores[ky], meta[ky].title.lower()),
    )
    return [meta[ky] for ky in sorted_keys]


def hybrid_search(
    query: str,
    *,
    limit: int = DEFAULT_SEARCH_LIMIT,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    category: str | None = None,
) -> list[SearchResult]:
    """Hybrid search combining FTS5 keyword results with vector similarity via RRF."""
    limit = max(1, min(limit, MAX_SEARCH_LIMIT))
    fetch_limit = limit * 3

    from .search import DocSearcher

    searcher = DocSearcher()

    keyword_results: list[SearchResult] = []
    try:
        if category == "guide" or category is None:
            keyword_results.extend(
                searcher.search_guides(
                    query,
                    limit=fetch_limit,
                    engine=engine,
                    version=version,
                    docset=docset,
                )
            )
        if category == "api" or category is None:
            keyword_results.extend(
                searcher.search_api(
                    query,
                    limit=fetch_limit,
                    engine=engine,
                    version=version,
                    docset=docset,
                )
            )
    except (ValueError, IndexNotReadyError):
        pass

    vector_results: list[SearchResult] = []
    try:
        vector_results = vector_search(
            query,
            limit=fetch_limit,
            engine=engine,
            version=version,
            docset=docset,
            category=category,
        )
    except Exception as exc:
        logger.warning("Vector search failed, using keyword-only: %s", exc)

    if not vector_results:
        keyword_results.sort(key=lambda r: (r.score, r.title.lower()))
        return keyword_results[:limit]

    if not keyword_results:
        return vector_results[:limit]

    merged = _rrf_merge(keyword_results, vector_results)
    return merged[:limit]


# ---------------------------------------------------------------------------
# Spec resolution (tolerant of unregistered docsets)
# ---------------------------------------------------------------------------


def _resolve_specs(
    *,
    engine: str | None,
    version: str | None,
    docset: str | None,
) -> list[DocsetSpec]:
    """Resolve indexed docsets, falling back gracefully."""
    specs = select_docsets(engine=engine, version=version, docset=docset)
    if not specs:
        raise ValueError("No matching documentation targets were found.")

    indexed = [s for s in specs if s.indexed]
    if indexed:
        return indexed

    labels = ", ".join(s.key for s in specs)
    raise IndexNotReadyError(
        f"No index database is available for the selected docset(s): {labels}. "
        "Build the index first with scripts/build_index.py."
    )
