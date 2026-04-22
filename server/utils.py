"""Utility helpers for output formatting."""

from __future__ import annotations

import json
from typing import Any

from .models import GuideReference, SearchResult, SymbolReference


def truncate(text: str, max_len: int = 500, suffix: str = "...") -> str:
    if not text or len(text) <= max_len:
        return text or ""
    return text[: max_len - len(suffix)] + suffix


def safe_json_parse(text: str) -> Any:
    if not text:
        return []
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []


def _target_label(engine: str, version: str, docset: str, docset_label: str = "") -> str:
    if docset_label:
        return f"{docset_label} [{engine}/{version}/{docset}]"
    if engine or version or docset:
        return f"{engine}/{version}/{docset}".strip("/")
    return ""


def format_docset_status(rows: list[dict[str, str | bool]]) -> str:
    if not rows:
        return "No documentation targets are registered."

    lines = ["Registered documentation targets", "=" * 32]
    for row in rows:
        lines.append(f"- {row['label']} ({row['key']})")
        lines.append(f"  Docs root: {row['docs_root']}")
        lines.append(f"  Database: {row['db_path']}")
        lines.append(f"  Parser: {row['parser_kind']}")
        lines.append(
            f"  Status: docs={'yes' if row['docs_available'] else 'no'} | "
            f"index={'yes' if row['index_available'] else 'no'}"
        )
        if row.get("description"):
            lines.append(f"  Notes: {row['description']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_search_results(results: list[SearchResult], header: str | None = None) -> str:
    if not results:
        return "No results found."

    lines: list[str] = []
    if header:
        lines.append(header)
        lines.append("=" * len(header))
    for i, result in enumerate(results, 1):
        lines.append(f"--- Result {i} [{result.category}] ---")
        target = _target_label(result.engine, result.version, result.docset, result.docset_label)
        if target:
            lines.append(f"Target: {target}")
        lines.append(f"Title: {result.title}")
        if result.symbol_name:
            lines.append(f"Symbol: {result.symbol_name}")
        if result.class_name and result.class_name != result.symbol_name:
            lines.append(f"Class: {result.class_name}")
        if result.namespace:
            lines.append(f"Namespace: {result.namespace}")
        if result.module_name:
            lines.append(f"Module: {result.module_name}")
        if result.member_type:
            lines.append(f"Member type: {result.member_type}")
        if result.guide_type:
            lines.append(f"Guide type: {result.guide_type}")
        if result.topic_path:
            lines.append(f"Topic path: {result.topic_path}")
        lines.append(f"Path: {result.relative_path}")
        lines.append(f"Snippet: {truncate(result.snippet, 400)}")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_combined_results(bundle: dict[str, list[SearchResult]]) -> str:
    api = bundle.get("api", [])
    guide = bundle.get("guide", [])

    parts = [
        "Documentation answer (combined search)",
        "=" * 36,
        f"API matches: {len(api)} | Guide matches: {len(guide)}",
        "",
        format_search_results(api, header="API / Reference results"),
        "",
        format_search_results(guide, header="Guide / Concept results"),
    ]
    return "\n".join(parts)


def _append_json_list(lines: list[str], heading: str, payload: str, formatter) -> None:
    items = safe_json_parse(payload)
    if not items:
        return
    lines += ["", heading]
    for item in items:
        rendered = formatter(item)
        if rendered:
            lines.append(rendered)


def format_symbol_ref(ref: SymbolReference) -> str:
    lines: list[str] = [f"# {ref.title or ref.symbol_name or '(untitled)'}"]
    target = _target_label(ref.engine, ref.version, ref.docset, ref.docset_label)
    if target:
        lines.append(f"Target: {target}")
    if ref.symbol_name:
        lines.append(f"Symbol: {ref.symbol_name}")
    if ref.class_name and ref.class_name != ref.symbol_name:
        lines.append(f"Class: {ref.class_name}")
    if ref.namespace:
        lines.append(f"Namespace: {ref.namespace}")
    if ref.module_name:
        lines.append(f"Module: {ref.module_name}")
    if ref.member_type:
        lines.append(f"Member type: {ref.member_type}")
    if ref.topic_path:
        lines.append(f"Topic path: {ref.topic_path}")
    lines.append(f"Path: {ref.relative_path}")
    if ref.header_path:
        lines.append(f"Header: {ref.header_path}")
    if ref.include_text:
        lines.append(f"Include: {ref.include_text}")
    if ref.source_path:
        lines.append(f"Source file: {ref.source_path}")

    if ref.signature:
        lines += ["", "## Signature", ref.signature]
    if ref.summary:
        lines += ["", "## Summary", ref.summary]

    _append_json_list(
        lines,
        "## Parameters",
        ref.parameters_json,
        lambda item: f"- {item.get('name', '?')}: {item.get('description', '')}".rstrip(),
    )

    if ref.returns_text:
        lines += ["", "## Returns", ref.returns_text]
    if ref.remarks:
        lines += ["", "## Remarks", ref.remarks]
    _append_json_list(
        lines,
        "## Inheritance",
        ref.inheritance_json,
        lambda item: f"- {item}" if item else "",
    )
    _append_json_list(
        lines,
        "## Inputs",
        ref.inputs_json,
        lambda item: (
            f"- {item.get('name', '?')}: {item.get('type', '')}"
            + (f" | {item.get('description')}" if item.get("description") else "")
        ).rstrip(),
    )
    _append_json_list(
        lines,
        "## Outputs",
        ref.outputs_json,
        lambda item: (
            f"- {item.get('name', '?')}: {item.get('type', '')}"
            + (f" | {item.get('description')}" if item.get("description") else "")
        ).rstrip(),
    )
    if ref.content_excerpt:
        lines += ["", "## Content Excerpt", truncate(ref.content_excerpt, 1500)]
    return "\n".join(lines)


def format_guide_ref(ref: GuideReference) -> str:
    lines: list[str] = [f"# {ref.title or '(untitled)'}"]
    target = _target_label(ref.engine, ref.version, ref.docset, ref.docset_label)
    if target:
        lines.append(f"Target: {target}")
    if ref.guide_type:
        lines.append(f"Guide type: {ref.guide_type}")
    if ref.topic_path:
        lines.append(f"Topic path: {ref.topic_path}")
    lines.append(f"Path: {ref.relative_path}")

    if ref.summary:
        lines += ["", "## Summary", ref.summary]

    _append_json_list(
        lines,
        "## Key topics",
        ref.key_topics_json,
        lambda item: f"- {item}" if item else "",
    )
    if ref.content_excerpt:
        lines += ["", "## Content Excerpt", truncate(ref.content_excerpt, 2000)]
    return "\n".join(lines)


def format_doc_page(payload: dict) -> str:
    ref = payload["ref"]
    if isinstance(ref, SymbolReference):
        return format_symbol_ref(ref)
    if isinstance(ref, GuideReference):
        return format_guide_ref(ref)
    return "(unrecognized record)"
