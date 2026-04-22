"""Indexer: scans HTML files and writes them to the right table."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from .config import DOCS_ROOT
from .db import get_connection, init_db, rebuild_db, upsert_api_record, upsert_guide_record
from .models import ApiRecord, GuideRecord
from .parser import discover_html_files, parse_html_file

logger = logging.getLogger(__name__)


def build_index(
    docs_root: Path | None = None,
    db_path: Path | None = None,
    rebuild: bool = True,
    batch_size: int = 500,
) -> dict:
    """Build the documentation index, returning a stats dict."""
    docs_root = docs_root or DOCS_ROOT
    start = time.time()

    conn = get_connection(db_path)
    if rebuild:
        rebuild_db(conn)
    else:
        init_db(conn)

    html_files = discover_html_files(docs_root)
    total = len(html_files)
    logger.info("Discovered %d HTML files under %s", total, docs_root)

    api_count = 0
    guide_count = 0
    errors = 0

    for i, html_path in enumerate(html_files, 1):
        try:
            rec = parse_html_file(html_path, docs_root)
            if isinstance(rec, ApiRecord):
                upsert_api_record(conn, rec)
                api_count += 1
            elif isinstance(rec, GuideRecord):
                upsert_guide_record(conn, rec)
                guide_count += 1
        except Exception as e:
            errors += 1
            logger.warning("Error indexing %s: %s", html_path, e)

        if i % batch_size == 0:
            conn.commit()
            logger.info(
                "Progress: %d/%d  (api=%d, guide=%d, errors=%d)",
                i, total, api_count, guide_count, errors,
            )

    conn.commit()
    # Optimize FTS indexes once at the end for tighter ranking and smaller size.
    try:
        conn.execute("INSERT INTO api_fts(api_fts) VALUES('optimize')")
        conn.execute("INSERT INTO guide_fts(guide_fts) VALUES('optimize')")
        conn.commit()
    except Exception as e:
        logger.warning("FTS optimize step failed: %s", e)

    elapsed = time.time() - start
    stats = {
        "total": total,
        "api_indexed": api_count,
        "guide_indexed": guide_count,
        "errors": errors,
        "elapsed_seconds": round(elapsed, 2),
    }
    logger.info(
        "Indexing complete: api=%d, guide=%d, errors=%d in %.1fs",
        api_count, guide_count, errors, elapsed,
    )
    conn.close()
    return stats
