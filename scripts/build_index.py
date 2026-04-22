#!/usr/bin/env python3
"""Build or rebuild one or more documentation SQLite indexes."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.docsets import docset_status_rows, get_docset, select_docsets
from src.indexer import build_index, build_indexes
from src.utils import format_docset_status


def main() -> None:
    parser = argparse.ArgumentParser(description="Build documentation indexes")
    parser.add_argument("--engine", help="Engine name, e.g. unity or unreal")
    parser.add_argument("--version", help="Engine version, e.g. current or 4.26")
    parser.add_argument("--docset", help="Docset name, e.g. reference, cpp-api, blueprint-api")
    parser.add_argument("--all", action="store_true", help="Build all matching registered docsets")
    parser.add_argument("--list-docsets", action="store_true", help="List registered docsets and exit")
    parser.add_argument("--docs-root", type=Path, help="Override docs root for a single selected docset")
    parser.add_argument("--db-path", type=Path, help="Override database path for a single selected docset")
    parser.add_argument("--no-rebuild", action="store_true", help="Do not drop existing data; only insert/update")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if args.list_docsets:
        print(format_docset_status(docset_status_rows(select_docsets())))
        return

    if args.docs_root or args.db_path:
        spec = get_docset(
            engine=args.engine or "unity",
            version=args.version,
            docset=args.docset,
        )
        stats = build_index(
            spec,
            docs_root=args.docs_root,
            db_path=args.db_path,
            rebuild=not args.no_rebuild,
        )
        rows = [stats]
    elif args.all or any([args.engine, args.version, args.docset]):
        rows = build_indexes(
            engine=args.engine,
            version=args.version,
            docset=args.docset,
            rebuild=not args.no_rebuild,
        )
    else:
        spec = get_docset(engine="unity", version="current", docset="reference")
        rows = [build_index(spec, rebuild=not args.no_rebuild)]

    total_api = sum(row["api_indexed"] for row in rows)
    total_guides = sum(row["guide_indexed"] for row in rows)
    total_errors = sum(row["errors"] for row in rows)

    for row in rows:
        print(f"\n[{row['engine']}/{row['version']}/{row['docset']}] {row['label']}")
        print(f"  Docs root: {row['docs_root']}")
        print(f"  Database:  {row['db_path']}")
        print(f"  Files:     {row['total']}")
        print(f"  API:       {row['api_indexed']}")
        print(f"  Guides:    {row['guide_indexed']}")
        print(f"  Errors:    {row['errors']}")
        print(f"  Time:      {row['elapsed_seconds']}s")

    if len(rows) > 1:
        print("\nTotals")
        print("------")
        print(f"  API:    {total_api}")
        print(f"  Guides: {total_guides}")
        print(f"  Errors: {total_errors}")


if __name__ == "__main__":
    main()
