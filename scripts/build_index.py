#!/usr/bin/env python3
"""Build or rebuild the Unity documentation SQLite index."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unity_mcp.config import DB_PATH, DOCS_ROOT
from unity_mcp.indexer import build_index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Unity docs SQLite index")
    parser.add_argument(
        "--docs-root",
        type=Path,
        default=DOCS_ROOT,
        help="Root directory of Unity HTML documentation",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=DB_PATH,
        help="Path to the SQLite database file",
    )
    parser.add_argument(
        "--no-rebuild",
        action="store_true",
        help="Do not drop existing data; only insert/update",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print(f"Scanning: {args.docs_root}")
    print(f"Database: {args.db_path}")

    stats = build_index(
        docs_root=args.docs_root,
        db_path=args.db_path,
        rebuild=not args.no_rebuild,
    )

    print(f"\nDone!")
    print(f"  Total files found:   {stats['total']}")
    print(f"  API pages indexed:   {stats['api_indexed']}")
    print(f"  Guide pages indexed: {stats['guide_indexed']}")
    print(f"  Errors: {stats['errors']}")
    print(f"  Time:   {stats['elapsed_seconds']}s")


if __name__ == "__main__":
    main()
