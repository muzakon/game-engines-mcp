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


# ---------------------------------------------------------------------------
# Search-result rendering
# ---------------------------------------------------------------------------

def format_search_results(results: list[SearchResult], header: str | None = None) -> str:
    if not results:
        return "No results found."

    lines: list[str] = []
    if header:
        lines.append(header)
        lines.append("=" * len(header))
    for i, r in enumerate(results, 1):
        lines.append(f"--- Result {i} [{r.category}] ---")
        lines.append(f"Title: {r.title}")
        if r.symbol_name:
            lines.append(f"Symbol: {r.symbol_name}")
        if r.class_name and r.class_name != r.symbol_name:
            lines.append(f"Class: {r.class_name}")
        if r.namespace:
            lines.append(f"Namespace: {r.namespace}")
        if r.member_type:
            lines.append(f"Member type: {r.member_type}")
        if r.guide_type:
            lines.append(f"Guide type: {r.guide_type}")
        lines.append(f"Path: {r.relative_path}")
        lines.append(f"Snippet: {truncate(r.snippet, 400)}")
        lines.append("")
    return "\n".join(lines)


def format_combined_results(bundle: dict[str, list[SearchResult]]) -> str:
    parts: list[str] = []
    api = bundle.get("api", [])
    guide = bundle.get("guide", [])

    parts.append("Unity documentation answer (combined search)")
    parts.append("=" * 44)
    parts.append(
        f"API matches: {len(api)} | Guide matches: {len(guide)}"
    )
    parts.append("")
    parts.append(format_search_results(api, header="API / Reference results"))
    parts.append("")
    parts.append(format_search_results(guide, header="Guide / Manual results"))
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Detail rendering
# ---------------------------------------------------------------------------

def format_symbol_ref(ref: SymbolReference) -> str:
    lines: list[str] = [f"# {ref.title or ref.symbol_name or '(untitled)'}"]
    if ref.symbol_name:
        lines.append(f"Symbol: {ref.symbol_name}")
    if ref.class_name and ref.class_name != ref.symbol_name:
        lines.append(f"Class: {ref.class_name}")
    if ref.namespace:
        lines.append(f"Namespace: {ref.namespace}")
    if ref.member_type:
        lines.append(f"Member type: {ref.member_type}")
    lines.append(f"Path: {ref.relative_path}")
    lines.append("Source: Unity ScriptReference (API)")

    if ref.signature:
        lines += ["", "## Signature", ref.signature]
    if ref.summary:
        lines += ["", "## Summary", ref.summary]

    params = safe_json_parse(ref.parameters_json)
    if params:
        lines += ["", "## Parameters"]
        for p in params:
            lines.append(f"  - {p.get('name', '?')}: {p.get('description', '')}")
    if ref.returns_text:
        lines += ["", "## Returns", ref.returns_text]
    if ref.remarks:
        lines += ["", "## Remarks", ref.remarks]
    if ref.content_excerpt:
        lines += ["", "## Content Excerpt", truncate(ref.content_excerpt, 1500)]
    return "\n".join(lines)


def format_guide_ref(ref: GuideReference) -> str:
    lines: list[str] = [f"# {ref.title or '(untitled)'}"]
    if ref.guide_type:
        lines.append(f"Guide type: {ref.guide_type}")
    lines.append(f"Path: {ref.relative_path}")
    lines.append("Source: Unity Manual (Guide)")

    if ref.summary:
        lines += ["", "## Summary", ref.summary]

    topics = safe_json_parse(ref.key_topics_json)
    if topics:
        lines += ["", "## Key topics"]
        for t in topics:
            lines.append(f"  - {t}")
    if ref.content_excerpt:
        lines += ["", "## Content Excerpt", truncate(ref.content_excerpt, 2000)]
    return "\n".join(lines)


def format_doc_page(payload: dict) -> str:
    """Format whatever get_doc_page() returned (api or guide)."""
    ref = payload["ref"]
    if isinstance(ref, SymbolReference):
        return format_symbol_ref(ref)
    if isinstance(ref, GuideReference):
        return format_guide_ref(ref)
    return "(unrecognized record)"
