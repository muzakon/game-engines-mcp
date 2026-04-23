"""Data models for indexed documentation records and search results.

Three groups of models live here:

* **Index records** – ``ApiRecord`` and ``GuideRecord`` map 1:1 to rows in
  the ``api_records`` / ``guide_records`` SQLite tables.
* **Search results** – ``SearchResult`` is the flat DTO returned by search
  helpers, carrying both data and a BM25-style ``score``.
* **Reference models** – ``SymbolReference`` and ``GuideReference`` enrich
  a database row with engine metadata and a short content excerpt, ready
  for formatting by ``utils.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Index records (one per row in their respective tables)
# ---------------------------------------------------------------------------


@dataclass
class ApiRecord:
    """A single indexed API / symbol page.

    Fields correspond to columns in the ``api_records`` table.  JSON-prefixed
    fields (``parameters_json``, ``inheritance_json``, etc.) store
    JSON-encoded arrays.
    """

    id: Optional[int] = None
    title: str = ""
    relative_path: str = ""
    symbol_name: str = ""
    class_name: str = ""
    namespace: str = ""
    member_type: str = ""
    signature: str = ""
    parameters_json: str = ""
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
    guide_type: str = ""
    topic_path: str = ""
    summary: str = ""
    content_text: str = ""
    key_topics_json: str = ""
    source_html_path: str = ""


# ---------------------------------------------------------------------------
# Search result containers
# ---------------------------------------------------------------------------


@dataclass
class SearchResult:
    """A single search hit returned by the search helpers.

    ``category`` is either ``"api"`` or ``"guide"``.  Fields that only apply
    to one category (e.g. ``symbol_name`` for API, ``guide_type`` for guides)
    are empty strings when not applicable.
    """

    id: int
    category: str
    title: str
    relative_path: str
    snippet: str
    score: float
    engine: str = ""
    version: str = ""
    docset: str = ""
    docset_label: str = ""
    symbol_name: str = ""
    class_name: str = ""
    namespace: str = ""
    member_type: str = ""
    module_name: str = ""
    topic_path: str = ""
    guide_type: str = ""


# ---------------------------------------------------------------------------
# Reference models (enriched row + engine metadata)
# ---------------------------------------------------------------------------


@dataclass
class SymbolReference:
    """Structured reference for a single API symbol lookup.

    Construct via :meth:`from_row` which trims ``content_text`` into
    ``content_excerpt``.
    """

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
        """Build from a raw DB row dict, attaching engine metadata."""
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
        """Build from a raw DB row dict, attaching engine metadata."""
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
