"""Data models for indexed Unity documentation records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# --- Indexed records (one per row in their respective tables) ---

@dataclass
class ApiRecord:
    """A single indexed Unity ScriptReference / API page."""

    id: Optional[int] = None
    title: str = ""
    relative_path: str = ""
    symbol_name: str = ""        # e.g. "Transform.Rotate"
    class_name: str = ""         # e.g. "Transform"
    namespace: str = ""          # e.g. "UnityEngine"
    member_type: str = ""        # class | struct | enum | interface | method | property | field | event
    signature: str = ""
    parameters_json: str = ""    # JSON array of {name, description}
    returns_text: str = ""
    summary: str = ""
    remarks: str = ""
    content_text: str = ""
    source_html_path: str = ""


@dataclass
class GuideRecord:
    """A single indexed Manual / conceptual / tutorial page."""

    id: Optional[int] = None
    title: str = ""
    relative_path: str = ""
    guide_type: str = ""          # manual | tutorial | overview | reference | general
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
    # API-only fields (empty for guides)
    symbol_name: str = ""
    class_name: str = ""
    namespace: str = ""
    member_type: str = ""
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
    member_type: str = ""
    signature: str = ""
    summary: str = ""
    parameters_json: str = ""
    returns_text: str = ""
    remarks: str = ""
    content_excerpt: str = ""

    @classmethod
    def from_row(cls, row: dict, excerpt_len: int = 1500) -> "SymbolReference":
        content = row.get("content_text", "") or ""
        return cls(
            id=row["id"],
            title=row.get("title", ""),
            relative_path=row.get("relative_path", ""),
            symbol_name=row.get("symbol_name", ""),
            class_name=row.get("class_name", ""),
            namespace=row.get("namespace", ""),
            member_type=row.get("member_type", ""),
            signature=row.get("signature", ""),
            summary=row.get("summary", ""),
            parameters_json=row.get("parameters_json", ""),
            returns_text=row.get("returns_text", ""),
            remarks=row.get("remarks", ""),
            content_excerpt=content[:excerpt_len],
        )


@dataclass
class GuideReference:
    """Structured reference for a single guide page lookup."""

    id: int
    title: str
    relative_path: str
    guide_type: str = ""
    summary: str = ""
    key_topics_json: str = ""
    content_excerpt: str = ""

    @classmethod
    def from_row(cls, row: dict, excerpt_len: int = 2000) -> "GuideReference":
        content = row.get("content_text", "") or ""
        return cls(
            id=row["id"],
            title=row.get("title", ""),
            relative_path=row.get("relative_path", ""),
            guide_type=row.get("guide_type", ""),
            summary=row.get("summary", ""),
            key_topics_json=row.get("key_topics_json", ""),
            content_excerpt=content[:excerpt_len],
        )
