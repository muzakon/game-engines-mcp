"""Output formatting helpers for search results and docset status.

Every public function takes a model object and returns a human-readable
string suitable for display in a CLI or MCP tool response.

The main entry points are:

* :func:`format_docset_status` – summary table of registered docsets.
* :func:`format_search_results` – bullet list of search hits.
* :func:`format_symbol_ref` / :func:`format_guide_ref` – detailed single-
  page references.
"""

from __future__ import annotations

import json
from typing import Any

from .models import GuideReference, SearchResult, SymbolReference


def truncate(text: str, max_len: int = 500, suffix: str = "...") -> str:
    """Truncate *text* to *max_len* characters, appending *suffix*."""
    if not text or len(text) <= max_len:
        return text or ""
    return text[: max_len - len(suffix)] + suffix


def safe_json_parse(text: str) -> Any:
    """Parse a JSON string, returning an empty list on failure."""
    if not text:
        return []
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []


def _target_label(engine: str, version: str, docset: str, docset_label: str = "") -> str:
    """Build a human-readable label like ``Unreal 4.26 cpp-api [unreal/4.26/cpp-api]``."""
    if docset_label:
        return f"{docset_label} [{engine}/{version}/{docset}]"
    if engine or version or docset:
        return f"{engine}/{version}/{docset}".strip("/")
    return ""


def format_docset_status(rows: list[dict[str, str | bool]]) -> str:
    """Render a list of docset status dicts as a plain-text table."""
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
    """Render a list of search results as a numbered text report."""
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
    """Format the combined API + guide results from :meth:`DocSearcher.answer_question`."""
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
    """Parse *payload* as JSON and append formatted items under *heading*."""
    items = safe_json_parse(payload)
    if not items:
        return
    lines += ["", heading]
    for item in items:
        rendered = formatter(item)
        if rendered:
            lines.append(rendered)


def format_symbol_ref(ref: SymbolReference) -> str:
    """Render a :class:`SymbolReference` as a detailed Markdown-style string."""
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
    """Render a :class:`GuideReference` as a detailed Markdown-style string."""
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
    """Dispatch to the correct formatter based on the reference type."""
    ref = payload["ref"]
    if isinstance(ref, SymbolReference):
        return format_symbol_ref(ref)
    if isinstance(ref, GuideReference):
        return format_guide_ref(ref)
    return "(unrecognized record)"


def format_translation_results(results: list, source_symbol: str, source_engine: str, target_engine: str) -> str:
    """Format cross-engine translation results as a readable string."""
    if not results:
        return (
            f"No equivalent found for '{source_symbol}' "
            f"({source_engine} -> {target_engine}). "
            "Try a broader term or check if the target engine is indexed."
        )

    lines = [
        f"Cross-engine translation: {source_engine} -> {target_engine}",
        f"Source: {source_symbol} ({source_engine})",
        "=" * 40,
    ]
    for i, r in enumerate(results, 1):
        conf_label = {"high": "HIGH", "medium": "MED", "low": "LOW"}.get(r.confidence, r.confidence)
        lines.append(f"--- Result {i} [{conf_label} confidence] ---")
        lines.append(f"Symbol: {r.target_symbol}")
        lines.append(f"Title: {r.target_title}")
        if r.target_member_type:
            lines.append(f"Member type: {r.target_member_type}")
        if r.target_summary:
            lines.append(f"Summary: {truncate(r.target_summary, 300)}")
        lines.append(f"Path: {r.target_relative_path}")
        lines.append(f"Target: {r.target_docset_label} [{r.target_engine}/{r.target_docset}]")
        lines.append("")
    return "\n".join(lines).rstrip()


def format_class_info(info) -> str:
    """Format a ClassInfo object as a detailed Markdown-style string."""
    lines = [f"# {info.title or info.symbol_name}"]
    target = _target_label(info.engine, info.version, info.docset, info.docset_label)
    if target:
        lines.append(f"Target: {target}")
    lines.append(f"Symbol: {info.symbol_name}")
    if info.summary:
        lines += ["", "## Summary", info.summary]

    if info.inheritance:
        lines += ["", "## Inheritance", " > ".join(info.inheritance)]

    for label, members in [
        ("Methods", info.methods),
        ("Properties", info.properties),
        ("Signals", info.signals),
        ("Other members", info.other_members),
    ]:
        if not members:
            continue
        lines += ["", f"## {label} ({len(members)})"]
        for m in members:
            sym = m.get("symbol_name", "")
            summary = m.get("summary", "")
            sig = m.get("signature", "")
            entry = f"- **{sym}**"
            if summary:
                entry += f" — {truncate(summary, 100)}"
            lines.append(entry)
            if sig:
                lines.append(f"  `{sig}`")

    lines.append(f"\nPath: {info.relative_path}")
    return "\n".join(lines)


def format_module_info(info) -> str:
    """Format a ModuleInfo object as a readable string."""
    lines = [
        f"# Module: {info.name}",
        f"Target: {info.docset_label} [{info.engine}/{info.version}/{info.docset}]",
        f"Total members: {info.total_members}",
        f"Classes ({len(info.classes)}):",
    ]
    for cls in info.classes[:50]:
        lines.append(f"  - {cls}")
    if len(info.classes) > 50:
        lines.append(f"  ... and {len(info.classes) - 50} more")
    return "\n".join(lines)


def format_related_symbols(results: list[dict]) -> str:
    """Format related symbols as a readable string."""
    if not results:
        return "No related symbols found."

    lines = ["Related symbols:", "=" * 18]
    for r in results:
        lines.append(f"- **{r['symbol_name']}** ({r['member_type']})")
        if r.get("summary"):
            lines.append(f"  {truncate(r['summary'], 120)}")
        lines.append(f"  Path: {r['relative_path']} [{r['engine']}]")
    return "\n".join(lines)


def format_class_list(results: list[dict]) -> str:
    """Format a list of classes as a readable string."""
    if not results:
        return "No classes found."

    lines = [f"Classes ({len(results)}):", "=" * 12]
    for r in results:
        summary = truncate(r.get("summary", ""), 80)
        suffix = f" — {summary}" if summary else ""
        lines.append(f"- **{r['symbol_name']}**{suffix}")
        lines.append(f"  [{r['engine']}/{r['version']}/{r['docset']}] {r['relative_path']}")
    return "\n".join(lines)


def format_inheritance_chain(chain: list[dict]) -> str:
    """Format an inheritance chain as a readable string."""
    if not chain:
        return "No inheritance information found."

    lines = ["Inheritance chain:", "  " + " -> ".join(r["symbol_name"] for r in chain), ""]
    for r in chain:
        lines.append(f"- **{r['symbol_name']}**")
        if r.get("summary"):
            lines.append(f"  {truncate(r['summary'], 120)}")
    return "\n".join(lines)


def format_member_list(members: list[dict]) -> str:
    """Format a list of class members as a readable string."""
    if not members:
        return "No members found."

    lines = [f"Members ({len(members)}):", "=" * 12]
    for m in members:
        lines.append(f"- **{m['symbol_name']}** ({m['member_type']})")
        if m.get("signature"):
            lines.append(f"  `{m['signature']}`")
        if m.get("summary"):
            lines.append(f"  {truncate(m['summary'], 120)}")
    return "\n".join(lines)


def format_hybrid_results(results: list[SearchResult], query: str) -> str:
    """Format hybrid search results with a note about the fusion method."""
    lines = [
        f"Hybrid search (keyword + semantic): '{query}'",
        "=" * 42,
        f"Found {len(results)} results via Reciprocal Rank Fusion",
        "",
    ]
    lines.append(format_search_results(results, header="Results"))
    return "\n".join(lines)
