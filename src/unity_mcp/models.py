"""Data models for indexed documentation records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# --- Indexed records (one per row in their respective tables) ---

@dataclass
class ApiRecord:
    """A single indexed API / symbol page."""

    id: Optional[int] = None
    title: str = ""
    relative_path: str = ""
    symbol_name: str = ""        # e.g. "Transform.Rotate"
    class_name: str = ""         # e.g. "Transform"
    namespace: str = ""          # e.g. "UnityEngine"
    member_type: str = ""        # class | method | property | module | blueprint_node | ...
    signature: str = ""
    parameters_json: str = ""    # JSON array of {name, description}
    returns_text: str = ""
    summary: str = ""
    remarks: str = ""
    module_name: str = ""
    topic_path: str = ""
    header_path: str = ""
    include_text: str = ""
    source_path: str = ""
    inheritance_json: str = ""
    inputs_json: str = ""
    outputs_json: str = ""
    content_text: str = ""
    source_html_path: str = ""


@dataclass
class GuideRecord:
    """A single indexed conceptual / tutorial page."""

    id: Optional[int] = None
    title: str = ""
    relative_path: str = ""
    guide_type: str = ""          # manual | tutorial | overview | reference | quickstart | general
    topic_path: str = ""
    summary: str = ""
    content_text: str = ""
    key_topics_json: str = ""     # JSON array of section/heading topics
    source_html_path: str = ""


# --- Search result containers ---

@dataclass
class SearchResult:
    """A single search hit (API or guide)."""

    id: int
    category: str                 # "api" | "guide"
    title: str
    relative_path: str
    snippet: str
    score: float
    engine: str = ""
    version: str = ""
    docset: str = ""
    docset_label: str = ""
    # API-only fields (empty for guides)
    symbol_name: str = ""
    class_name: str = ""
    namespace: str = ""
    member_type: str = ""
    module_name: str = ""
    topic_path: str = ""
    # Guide-only field (empty for API)
    guide_type: str = ""


@dataclass
class SymbolReference:
    """Structured reference for a single API symbol lookup."""

    id: int
    title: str
    relative_path: str
    symbol_name: str = ""
    class_name: str = ""
    namespace: str = ""
    engine: str = ""
    version: str = ""
    docset: str = ""
    docset_label: str = ""
    member_type: str = ""
    signature: str = ""
    summary: str = ""
    parameters_json: str = ""
    returns_text: str = ""
    remarks: str = ""
    module_name: str = ""
    topic_path: str = ""
    header_path: str = ""
    include_text: str = ""
    source_path: str = ""
    inheritance_json: str = ""
    inputs_json: str = ""
    outputs_json: str = ""
    content_excerpt: str = ""

    @classmethod
    def from_row(
        cls,
        row: dict[str, Any],
        excerpt_len: int = 1500,
        **metadata: str,
    ) -> "SymbolReference":
        content = row.get("content_text", "") or ""
        return cls(
            id=row["id"],
            title=row.get("title", ""),
            relative_path=row.get("relative_path", ""),
            engine=metadata.get("engine", ""),
            version=metadata.get("version", ""),
            docset=metadata.get("docset", ""),
            docset_label=metadata.get("docset_label", ""),
            symbol_name=row.get("symbol_name", ""),
            class_name=row.get("class_name", ""),
            namespace=row.get("namespace", ""),
            member_type=row.get("member_type", ""),
            signature=row.get("signature", ""),
            summary=row.get("summary", ""),
            parameters_json=row.get("parameters_json", ""),
            returns_text=row.get("returns_text", ""),
            remarks=row.get("remarks", ""),
            module_name=row.get("module_name", ""),
            topic_path=row.get("topic_path", ""),
            header_path=row.get("header_path", ""),
            include_text=row.get("include_text", ""),
            source_path=row.get("source_path", ""),
            inheritance_json=row.get("inheritance_json", ""),
            inputs_json=row.get("inputs_json", ""),
            outputs_json=row.get("outputs_json", ""),
            content_excerpt=content[:excerpt_len],
        )


@dataclass
class GuideReference:
    """Structured reference for a single guide page lookup."""

    id: int
    title: str
    relative_path: str
    engine: str = ""
    version: str = ""
    docset: str = ""
    docset_label: str = ""
    guide_type: str = ""
    topic_path: str = ""
    summary: str = ""
    key_topics_json: str = ""
    content_excerpt: str = ""

    @classmethod
    def from_row(
        cls,
        row: dict[str, Any],
        excerpt_len: int = 2000,
        **metadata: str,
    ) -> "GuideReference":
        content = row.get("content_text", "") or ""
        return cls(
            id=row["id"],
            title=row.get("title", ""),
            relative_path=row.get("relative_path", ""),
            engine=metadata.get("engine", ""),
            version=metadata.get("version", ""),
            docset=metadata.get("docset", ""),
            docset_label=metadata.get("docset_label", ""),
            guide_type=row.get("guide_type", ""),
            topic_path=row.get("topic_path", ""),
            summary=row.get("summary", ""),
            key_topics_json=row.get("key_topics_json", ""),
            content_excerpt=content[:excerpt_len],
        )
