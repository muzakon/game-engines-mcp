"""Index builders for registered docsets."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .db import get_connection, init_db, rebuild_db, upsert_api_record, upsert_guide_record
from .docsets import DocsetSpec, get_docset, select_docsets
from .models import ApiRecord, GuideRecord
from .parser import discover_html_files, parse_html_records

logger = logging.getLogger(__name__)


def build_index(
    docset: DocsetSpec | None = None,
    *,
    docs_root: Path | None = None,
    db_path: Path | None = None,
    rebuild: bool = True,
    batch_size: int = 500,
) -> dict:
    """Build a single documentation index, returning a stats dict."""

    spec = (docset or get_docset()).with_overrides(docs_root=docs_root, db_path=db_path)
    if not spec.docs_root.exists():
        raise FileNotFoundError(spec.docs_root)

    start = time.time()
    conn = get_connection(spec.db_path)
    if rebuild:
        rebuild_db(conn, spec)
    else:
        init_db(conn, spec)

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
                    upsert_api_record(conn, record)
                    api_count += 1
                elif isinstance(record, GuideRecord):
                    upsert_guide_record(conn, record)
                    guide_count += 1
        except Exception as exc:  # pragma: no cover - kept for resilience during bulk indexing
            errors += 1
            logger.warning("Error indexing %s: %s", html_path, exc)

        if index % batch_size == 0:
            conn.commit()
            logger.info(
                "[%s] Progress: %d/%d (api=%d, guide=%d, errors=%d)",
                spec.key,
                index,
                total,
                api_count,
                guide_count,
                errors,
            )

    conn.commit()
    try:
        conn.execute("INSERT INTO api_fts(api_fts) VALUES('optimize')")
        conn.execute("INSERT INTO guide_fts(guide_fts) VALUES('optimize')")
        conn.commit()
    except Exception as exc:  # pragma: no cover - optimization failure should not abort the build
        logger.warning("[%s] FTS optimize step failed: %s", spec.key, exc)

    conn.close()
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
    logger.info(
        "[%s] Indexing complete: api=%d, guide=%d, errors=%d in %.1fs",
        spec.key,
        api_count,
        guide_count,
        errors,
        elapsed,
    )
    return stats


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

    specs = select_docsets(
        engine=engine,
        version=version,
        docset=docset,
        available_only=available_only,
    )
    if not specs:
        raise ValueError("No matching docsets were found to index.")

    return [
        build_index(spec, rebuild=rebuild, batch_size=batch_size)
        for spec in specs
    ]
