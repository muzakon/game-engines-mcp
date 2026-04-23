"""Parser dispatch and HTML file discovery.

This module provides two public helpers:

* :func:`discover_html_files` – recursively find all indexable HTML files
  under a docset's documentation root.
* :func:`parse_html_records` – dispatch a single HTML file to the correct
  parser based on the docset's ``parser_kind``.
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import HTML_EXTENSIONS, SKIP_FILENAMES, UNITY_SKIP_DIRS
from .docsets import DocsetSpec, get_docset
from .models import ApiRecord, GuideRecord
from .parsers import (
    classify_page,
    guide_type_for,
    parse_godot_html,
    parse_blueprint_html,
    parse_unity_html,
    parse_unreal_cpp_html,
)

ParsedRecord = ApiRecord | GuideRecord
ParsedRecords = list[ParsedRecord]


def discover_html_files(docset: DocsetSpec | None = None, root: Path | None = None) -> list[Path]:
    """Recursively find all indexable HTML files for a docset."""

    docset = docset or get_docset()
    docs_root = root or docset.docs_root
    skip_dirs = set(docset.skip_dirs)
    if docset.parser_kind == "unity_html" and not skip_dirs:
        skip_dirs = set(UNITY_SKIP_DIRS)

    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(docs_root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
        current_path = Path(current_root)
        for filename in sorted(filenames):
            if Path(filename).suffix.lower() not in HTML_EXTENSIONS:
                continue
            if filename in SKIP_FILENAMES:
                continue
            files.append(current_path / filename)
    return files


def parse_html_records(
    html_path: Path,
    docset: DocsetSpec | None = None,
    docs_root: Path | None = None,
) -> ParsedRecords:
    """Parse one file into one or more records."""

    docset = docset or get_docset()
    resolved_root = docs_root or docset.docs_root

    if docset.parser_kind == "unity_html":
        return [parse_unity_html(html_path, resolved_root)]
    if docset.parser_kind == "unreal_cpp_html":
        return [parse_unreal_cpp_html(html_path, resolved_root)]
    if docset.parser_kind == "unreal_blueprint_html":
        return [parse_blueprint_html(html_path, resolved_root)]
    if docset.parser_kind == "godot_html":
        return parse_godot_html(html_path, resolved_root)
    raise ValueError(f"Unsupported parser kind: {docset.parser_kind}")


def parse_html_file(
    html_path: Path,
    docset: DocsetSpec | None = None,
    docs_root: Path | None = None,
) -> ParsedRecord:
    """Parse one file into its primary record."""

    records = parse_html_records(html_path, docset=docset, docs_root=docs_root)
    if not records:
        raise ValueError(f"No records were parsed from {html_path}")
    return records[0]


__all__ = [
    "ParsedRecord",
    "ParsedRecords",
    "classify_page",
    "discover_html_files",
    "guide_type_for",
    "parse_html_records",
    "parse_html_file",
]
