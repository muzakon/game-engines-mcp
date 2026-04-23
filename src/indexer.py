"""Index builders for registered docsets.

Usage::

    from src.indexer import Indexer

    idx = Indexer()
    stats = idx.build_one(spec)        # single docset
    all_stats = idx.build_all()         # every registered docset

Set ``build_vectors=True`` (or pass ``--vectors`` on the CLI) to also
generate embedding vectors and store them in a LanceDB sidecar for
hybrid semantic search.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .db import Database, get_connection, init_db, rebuild_db, upsert_api_record, upsert_guide_record
from .docsets import DocsetSpec, get_docset, select_docsets
from .models import ApiRecord, GuideRecord
from .parser import discover_html_files, parse_html_records

logger = logging.getLogger(__name__)


class Indexer:
    """Build SQLite indexes from parsed HTML documentation.

    Parameters:
        batch_size: Number of records to buffer before committing.
        rebuild: When *True* (default), drop existing data first.
        build_vectors: When *True*, also build a LanceDB vector index.
    """

    def __init__(
        self,
        *,
        batch_size: int = 500,
        rebuild: bool = True,
        build_vectors: bool = False,
    ) -> None:
        self.batch_size = batch_size
        self.rebuild = rebuild
        self.build_vectors = build_vectors

    # -- public API ----------------------------------------------------------

    def build_one(
        self,
        docset: DocsetSpec,
        *,
        docs_root: Path | None = None,
        db_path: Path | None = None,
    ) -> dict:
        """Index a single docset and return a stats dict.

        Args:
            docset: The docset specification to index.
            docs_root: Override the docs root directory.
            db_path: Override the database file path.

        Returns:
            Dict with keys like ``total``, ``api_indexed``, ``guide_indexed``,
            ``errors``, ``elapsed_seconds``, etc.
        """
        spec = docset.with_overrides(docs_root=docs_root, db_path=db_path)
        if not spec.docs_root.exists():
            raise FileNotFoundError(spec.docs_root)

        start = time.time()
        db = Database.open(spec.db_path)

        if self.rebuild:
            db.rebuild(spec)
        else:
            db.init(spec)

        html_files = discover_html_files(spec)
        total = len(html_files)
        logger.info("Discovered %d HTML files under %s", total, spec.docs_root)

        api_count = 0
        guide_count = 0
        errors = 0

        for index, html_path in enumerate(html_files, 1):
            try:
                for record in parse_html_records(html_path, spec):
                    if isinstance(record, ApiRecord):
                        db.upsert_api(record)
                        api_count += 1
                    elif isinstance(record, GuideRecord):
                        db.upsert_guide(record)
                        guide_count += 1
            except Exception as exc:
                errors += 1
                logger.warning("Error indexing %s: %s", html_path, exc)

            if index % self.batch_size == 0:
                db.commit()
                logger.info(
                    "[%s] Progress: %d/%d (api=%d, guide=%d, errors=%d)",
                    spec.key, index, total, api_count, guide_count, errors,
                )

        db.commit()
        db.optimize_fts()
        db.close()

        # Build vector index if requested
        vector_stats = {}
        if self.build_vectors:
            try:
                from .vecsearch import build_vector_index
                vector_stats = build_vector_index(spec)
                logger.info(
                    "[%s] Vector index built: api=%d, guide=%d",
                    spec.key, vector_stats.get("api_embedded", 0),
                    vector_stats.get("guide_embedded", 0),
                )
            except Exception as exc:
                logger.warning("[%s] Vector index build failed: %s", spec.key, exc)

        elapsed = time.time() - start
        stats = {
            "engine": spec.engine,
            "version": spec.version,
            "docset": spec.docset,
            "label": spec.label,
            "docs_root": str(spec.docs_root),
            "db_path": str(spec.db_path),
            "total": total,
            "api_indexed": api_count,
            "guide_indexed": guide_count,
            "errors": errors,
            "elapsed_seconds": round(elapsed, 2),
        }
        if vector_stats:
            stats["vector_index"] = vector_stats
        logger.info(
            "[%s] Indexing complete: api=%d, guide=%d, errors=%d in %.1fs",
            spec.key, api_count, guide_count, errors, elapsed,
        )
        return stats

    def build_all(
        self,
        *,
        engine: str | None = None,
        version: str | None = None,
        docset: str | None = None,
        available_only: bool = True,
    ) -> list[dict]:
        """Build indexes for all matching registered docsets.

        Args:
            engine: Filter by engine name.
            version: Filter by engine version.
            docset: Filter by docset name.
            available_only: Skip docsets whose docs root doesn't exist.

        Returns:
            List of stats dicts, one per indexed docset.
        """
        specs = select_docsets(
            engine=engine,
            version=version,
            docset=docset,
            available_only=available_only,
        )
        if not specs:
            raise ValueError("No matching docsets were found to index.")

        return [self.build_one(spec) for spec in specs]


# ---------------------------------------------------------------------------
# Legacy function API (backward-compatible wrappers)
# ---------------------------------------------------------------------------

def build_index(
    docset: DocsetSpec | None = None,
    *,
    docs_root: Path | None = None,
    db_path: Path | None = None,
    rebuild: bool = True,
    batch_size: int = 500,
) -> dict:
    """Build a single documentation index, returning a stats dict."""
    spec = docset or get_docset()
    idx = Indexer(batch_size=batch_size, rebuild=rebuild)
    return idx.build_one(spec, docs_root=docs_root, db_path=db_path)


def build_indexes(
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    rebuild: bool = True,
    batch_size: int = 500,
    available_only: bool = True,
) -> list[dict]:
    """Build all matching registered docsets."""
    idx = Indexer(batch_size=batch_size, rebuild=rebuild)
    return idx.build_all(
        engine=engine, version=version, docset=docset,
        available_only=available_only,
    )
