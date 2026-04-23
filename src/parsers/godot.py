"""Godot Engine offline HTML parser.

Parses Godot's Sphinx-generated class reference pages (under
``classes/class_*.html``) into one class-level :class:`~src.models.ApiRecord`
plus per-member records.  Non-class pages are parsed as guide records.
"""

from __future__ import annotations

import html
import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..models import ApiRecord, GuideRecord

logger = logging.getLogger(__name__)

_SECTION_SELECTORS: tuple[tuple[str, str], ...] = (
    ("signal", "section#signals p.classref-signal"),
    ("property", "section#property-descriptions p.classref-property"),
    ("theme_property", "section#theme-property-descriptions p.classref-themeproperty"),
    ("constructor", "section#constructor-descriptions p.classref-constructor"),
    ("method", "section#method-descriptions p.classref-method"),
    ("operator", "section#operator-descriptions p.classref-operator"),
    ("constant", "section#constants p.classref-constant"),
    ("annotation", "section#annotations p.classref-annotation"),
)


def _clean(text: str) -> str:
    cleaned = html.unescape(text or "")
    cleaned = cleaned.replace("", " ").replace("🔗", " ")
    return re.sub(r"\s+", " ", cleaned).strip()


def _main_content_div(soup: BeautifulSoup) -> Tag:
    return (
        soup.select_one("div[role='main'].document")
        or soup.find("div", class_="document")
        or soup.find("body")
        or soup
    )


def _strip_chrome(content_div: Tag) -> None:
    for tag in content_div.find_all(["script", "style", "nav", "form", "noscript"]):
        tag.decompose()
    for selector in (
        "a.headerlink",
        "div.rst-footer-buttons",
        "div.rst-versions",
        "div.admonition.latest-notice",
    ):
        for tag in content_div.select(selector):
            tag.decompose()


def _content_root(soup: BeautifulSoup) -> Tag:
    root = _main_content_div(soup)
    _strip_chrome(root)
    return root


def _extract_title(content_div: Tag) -> str:
    h1 = content_div.find("h1")
    if h1:
        return _clean(h1.get_text(" ", strip=True))
    title = content_div.find("title")
    if title:
        return _clean(title.get_text(" ", strip=True))
    return ""


def _extract_meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    return _clean(tag.get("content", "")) if tag else ""


def _topic_path(relative_path: str) -> str:
    parts = Path(relative_path).parts[:-1]
    return "/".join(parts)


def _guide_type_for(relative_path: str, title: str) -> str:
    path_lower = relative_path.lower()
    title_lower = title.lower()

    if relative_path == "index.html":
        return "overview"
    if path_lower.startswith("getting_started/"):
        if any(token in path_lower for token in ("step_by_step", "first_2d_game", "first_3d_game")):
            return "tutorial"
        if "introduction" in path_lower:
            return "introduction"
        return "getting_started"
    if path_lower.startswith("tutorials/"):
        return "tutorial"
    if path_lower.startswith("about/"):
        return "about"
    if path_lower.startswith("engine_details/"):
        return "reference"
    if path_lower.startswith("community/"):
        return "community"
    if path_lower.startswith("classes/"):
        return "reference"
    if "overview" in title_lower:
        return "overview"
    return "general"


def _extract_main_text(content_div: Tag) -> str:
    return _clean(content_div.get_text(" ", strip=True))


def _extract_key_topics(content_div: Tag, limit: int = 20) -> list[str]:
    topics: list[str] = []
    seen: set[str] = set()
    for tag in content_div.find_all(["h2", "h3", "h4"]):
        text = _clean(tag.get_text(" ", strip=True))
        if not text or len(text) > 120:
            continue
        low = text.lower()
        if low in seen or low in {"table of contents"}:
            continue
        seen.add(low)
        topics.append(text)
        if len(topics) >= limit:
            break
    return topics


def _extract_guide_summary(content_div: Tag, soup: BeautifulSoup) -> str:
    h1 = content_div.find("h1")
    for p in content_div.find_all("p"):
        if h1 and h1 in p.parents:
            continue
        text = _clean(p.get_text(" ", strip=True))
        if text:
            return text[:800]
    return _extract_meta_description(soup)[:800]


def _class_section(content_div: Tag) -> Tag | None:
    for section in content_div.find_all("section", recursive=False):
        if section.find("h1"):
            return section
    return content_div.find("section")


def _extract_brief_description(class_section: Tag | None) -> str:
    if class_section is None:
        return ""
    for child in class_section.children:
        if not isinstance(child, Tag):
            continue
        if child.name == "section":
            break
        if child.name != "p":
            continue
        text = _clean(child.get_text(" ", strip=True))
        if not text or text.startswith("Inherits:") or text.startswith("Inherited By:"):
            continue
        return text[:800]
    return ""


def _extract_inheritance_chain(class_section: Tag | None, title: str) -> list[str]:
    if class_section is None:
        return []
    for p in class_section.find_all("p", recursive=False):
        text = _clean(p.get_text(" ", strip=True))
        if not text.startswith("Inherits:"):
            continue
        tail = text.split(":", 1)[1].strip()
        bases = [_clean(part) for part in tail.split("<") if _clean(part)]
        return [title, *bases] if title else bases
    return [title] if title else []


def _extract_description_text(class_section: Tag | None) -> str:
    if class_section is None:
        return ""
    description = class_section.find("section", id="description")
    if not description:
        return ""
    blocks: list[str] = []
    for child in description.children:
        if not isinstance(child, Tag):
            continue
        if child.name in {"h1", "h2", "h3", "h4"}:
            continue
        text = _clean(child.get_text(" ", strip=True))
        if text:
            blocks.append(text)
    return " ".join(blocks)


def _is_classref_item(tag: Tag) -> bool:
    return tag.name == "p" and any(cls.startswith("classref-") for cls in tag.get("class", ()))


def _collect_following_blocks(item_tag: Tag) -> list[str]:
    blocks: list[str] = []
    for sibling in item_tag.next_siblings:
        if not isinstance(sibling, Tag):
            continue
        if sibling.name == "p" and _is_classref_item(sibling):
            break
        if sibling.name == "section":
            break
        if sibling.name == "hr":
            continue
        text = _clean(sibling.get_text(" ", strip=True))
        if text:
            blocks.append(text)
    return blocks


def _parse_parameters(blob: str) -> list[dict[str, str]]:
    if not blob or blob == "void":
        return []

    parts: list[str] = []
    chunk: list[str] = []
    bracket_depth = 0
    for char in blob:
        if char in "[<":
            bracket_depth += 1
        elif char in "]>":
            bracket_depth = max(0, bracket_depth - 1)
        if char == "," and bracket_depth == 0:
            part = _clean("".join(chunk))
            if part:
                parts.append(part)
            chunk = []
            continue
        chunk.append(char)
    tail = _clean("".join(chunk))
    if tail:
        parts.append(tail)

    params: list[dict[str, str]] = []
    for part in parts:
        if part == "...":
            params.append({"name": "...", "description": "vararg"})
            continue
        if ":" in part:
            name, description = part.split(":", 1)
            params.append({"name": _clean(name), "description": _clean(description)})
        else:
            params.append({"name": _clean(part), "description": ""})
    return params


def _extract_signature_parts(
    signature_text: str,
    member_name: str,
    member_type: str,
    owner_name: str,
) -> tuple[str, str, list[dict[str, str]]]:
    returns_text = ""
    parameters: list[dict[str, str]] = []

    if "(" in signature_text and ")" in signature_text:
        open_index = signature_text.find("(")
        close_index = signature_text.rfind(")")
        params_blob = signature_text[open_index + 1 : close_index].strip()
        parameters = _parse_parameters(params_blob)
        name_index = signature_text.find(member_name)
        if name_index > 0 and member_type not in {"signal", "annotation"}:
            returns_text = _clean(signature_text[:name_index])
        elif member_type == "constructor":
            returns_text = owner_name

    return signature_text, returns_text, parameters


def _record_for_item(
    item_tag: Tag,
    *,
    owner_name: str,
    member_type: str,
    base_relative_path: str,
    topic_path: str,
    source_html_path: str,
) -> ApiRecord | None:
    item_id = item_tag.get("id", "").strip()
    member_tag = item_tag.find("strong")
    member_name = _clean(member_tag.get_text(" ", strip=True)) if member_tag else ""
    if not member_name:
        return None

    signature_text = _clean(item_tag.get_text(" ", strip=True))
    signature, returns_text, parameters = _extract_signature_parts(
        signature_text,
        member_name=member_name,
        member_type=member_type,
        owner_name=owner_name,
    )
    blocks = _collect_following_blocks(item_tag)
    summary = blocks[0][:800] if blocks else ""
    remarks = " ".join(blocks)
    symbol_name = f"{owner_name}.{member_name}" if owner_name else member_name
    relative_path = f"{base_relative_path}#{item_id}" if item_id else base_relative_path
    content_parts = [signature, *blocks]
    content_text = " ".join(part for part in content_parts if part)

    return ApiRecord(
        title=symbol_name,
        relative_path=relative_path,
        symbol_name=symbol_name,
        class_name=owner_name,
        namespace="",
        member_type=member_type,
        signature=signature,
        parameters_json=json.dumps(parameters, ensure_ascii=False) if parameters else "",
        returns_text=returns_text,
        summary=summary,
        remarks=remarks,
        topic_path=topic_path,
        content_text=content_text,
        source_html_path=source_html_path,
    )


def _parse_enumeration_records(
    content_div: Tag,
    *,
    owner_name: str,
    base_relative_path: str,
    topic_path: str,
    source_html_path: str,
) -> list[ApiRecord]:
    records: list[ApiRecord] = []
    for enum_tag in content_div.select("section#enumerations p.classref-enumeration"):
        record = _record_for_item(
            enum_tag,
            owner_name=owner_name,
            member_type="enum",
            base_relative_path=base_relative_path,
            topic_path=topic_path,
            source_html_path=source_html_path,
        )
        if record:
            records.append(record)

    for constant_tag in content_div.select("section#enumerations p.classref-enumeration-constant"):
        record = _record_for_item(
            constant_tag,
            owner_name=owner_name,
            member_type="enum_constant",
            base_relative_path=base_relative_path,
            topic_path=topic_path,
            source_html_path=source_html_path,
        )
        if record:
            records.append(record)
    return records


def _parse_class_records(
    soup: BeautifulSoup,
    content_div: Tag,
    *,
    relative_path: str,
    html_path: Path,
) -> list[ApiRecord]:
    title = _extract_title(content_div)
    class_section = _class_section(content_div)
    brief_description = _extract_brief_description(class_section)
    description_text = _extract_description_text(class_section)
    full_text = _extract_main_text(content_div)
    inheritance = _extract_inheritance_chain(class_section, title)
    base_member_type = "scope" if title.startswith("@") else "class"
    member_topic_path = "/".join(part for part in (_topic_path(relative_path), title) if part)

    records: list[ApiRecord] = [
        ApiRecord(
            title=title,
            relative_path=relative_path,
            symbol_name=title,
            class_name=title,
            namespace="",
            member_type=base_member_type,
            signature=f"Inherits: {' < '.join(inheritance[1:])}" if len(inheritance) > 1 else "",
            summary=brief_description or description_text[:800],
            remarks=description_text,
            topic_path=_topic_path(relative_path),
            inheritance_json=json.dumps(inheritance, ensure_ascii=False) if inheritance else "",
            content_text=full_text,
            source_html_path=str(html_path),
        )
    ]

    for member_type, selector in _SECTION_SELECTORS:
        for item_tag in content_div.select(selector):
            record = _record_for_item(
                item_tag,
                owner_name=title,
                member_type=member_type,
                base_relative_path=relative_path,
                topic_path=member_topic_path,
                source_html_path=str(html_path),
            )
            if record:
                records.append(record)

    records.extend(
        _parse_enumeration_records(
            content_div,
            owner_name=title,
            base_relative_path=relative_path,
            topic_path=member_topic_path,
            source_html_path=str(html_path),
        )
    )
    return records


def _parse_guide_record(
    soup: BeautifulSoup,
    content_div: Tag,
    *,
    relative_path: str,
    html_path: Path,
) -> GuideRecord:
    title = _extract_title(content_div)
    summary = _extract_guide_summary(content_div, soup)
    topics = _extract_key_topics(content_div)
    return GuideRecord(
        title=title,
        relative_path=relative_path,
        guide_type=_guide_type_for(relative_path, title),
        topic_path=_topic_path(relative_path),
        summary=summary,
        content_text=_extract_main_text(content_div),
        key_topics_json=json.dumps(topics, ensure_ascii=False) if topics else "",
        source_html_path=str(html_path),
    )


def parse_godot_html(html_path: Path, docs_root: Path) -> list[ApiRecord | GuideRecord]:
    relative_path = str(html_path.relative_to(docs_root))

    try:
        raw = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", html_path, exc)
        return [GuideRecord(relative_path=relative_path, source_html_path=str(html_path))]

    soup = BeautifulSoup(raw, "lxml")
    content_div = _content_root(soup)

    if relative_path.startswith("classes/class_") and relative_path.endswith(".html"):
        return _parse_class_records(
            soup,
            content_div,
            relative_path=relative_path,
            html_path=html_path,
        )

    return [
        _parse_guide_record(
            soup,
            content_div,
            relative_path=relative_path,
            html_path=html_path,
        )
    ]
