"""Unreal Engine offline HTML parsers."""

from __future__ import annotations

import html
import json
import logging
import re
import warnings
from pathlib import Path

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

from ..models import ApiRecord, GuideRecord

logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def _main_content_div(soup: BeautifulSoup) -> Tag:
    return (
        soup.find("div", id="maincol")
        or soup.find("div", id="pagecontainer")
        or soup.find("body")
        or soup
    )


def _strip_chrome(content_div: Tag) -> None:
    for tag in content_div.find_all(["script", "style", "nav", "form", "noscript"]):
        tag.decompose()
    for selector in (
        "#skinContainer",
        "#recommendations",
        "#feedbackButton",
        "#feedbackMessage",
        "#osContainer",
    ):
        for tag in content_div.select(selector):
            tag.decompose()


def _extract_title(soup: BeautifulSoup) -> str:
    h1 = soup.find("h1", id="H1TitleId") or soup.find("h1")
    if h1:
        text = _clean(h1.get_text(" ", strip=True))
        if text:
            return text
    title = soup.find("title")
    if title:
        return _clean(title.get_text().replace("| Unreal Engine Documentation", ""))
    return ""


def _extract_meta_description(soup: BeautifulSoup) -> str:
    tag = soup.find("meta", attrs={"name": "description"})
    return _clean(tag.get("content", "")) if tag else ""


def _extract_hero_subtitle(soup: BeautifulSoup) -> str:
    hero = soup.find("div", class_="hero")
    if not hero:
        return ""
    h2 = hero.find("h2")
    return _clean(h2.get_text(" ", strip=True)) if h2 else ""


def _extract_main_text(soup: BeautifulSoup) -> str:
    content_div = _main_content_div(soup)
    _strip_chrome(content_div)
    return _clean(content_div.get_text(separator=" ", strip=True))


def _extract_first_paragraph(soup: BeautifulSoup) -> str:
    main = _main_content_div(soup)
    for p in main.find_all("p"):
        text = _clean(p.get_text(" ", strip=True))
        if len(text) > 8:
            return text
    return ""


def _extract_summary(soup: BeautifulSoup, title: str) -> str:
    for candidate in (_extract_hero_subtitle(soup), _extract_meta_description(soup), _extract_first_paragraph(soup)):
        if candidate and candidate.lower() != title.lower():
            return candidate[:800]
        if candidate:
            same = candidate
    return (same if "same" in locals() else "")[:800]


def _extract_section_text(soup: BeautifulSoup, section_id: str) -> str:
    section = soup.find("div", id=section_id)
    if not section:
        return ""
    texts = []
    for p in section.find_all(["p", "li"]):
        text = _clean(p.get_text(" ", strip=True))
        if text:
            texts.append(text)
    return " ".join(texts)[:3000]


def _extract_code_signature(soup: BeautifulSoup) -> str:
    section = soup.find("div", id="syntax")
    if not section:
        return ""
    code = section.find("div", class_="simplecode_api")
    if not code:
        return ""
    return _clean(code.get_text(" ", strip=True))


def _extract_reference_map(soup: BeautifulSoup) -> dict[str, str]:
    refs: dict[str, str] = {}
    section = soup.find("div", id="references")
    if not section:
        return refs
    for row in section.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 2:
            continue
        key = _clean(cells[0].get_text(" ", strip=True)).rstrip(":")
        value = _clean(cells[1].get_text(" ", strip=True))
        if key:
            refs[key] = value
    return refs


def _extract_hierarchy(soup: BeautifulSoup) -> list[str]:
    section = soup.find("div", id="hierarchy")
    if not section:
        return []
    chain: list[str] = []
    seen: set[str] = set()
    for cell in section.select(".hierarchy-label-cell"):
        text = _clean(cell.get_text(" ", strip=True))
        if not text or text in seen:
            continue
        seen.add(text)
        chain.append(text)
    return chain


def _extract_topics(soup: BeautifulSoup, limit: int = 20) -> list[str]:
    topics: list[str] = []
    seen: set[str] = set()
    main = _main_content_div(soup)
    heading_tags = list(main.find_all(["h2", "h3", "h4"])) + list(main.select("div.heading > p"))
    for tag in heading_tags:
        text = _clean(tag.get_text(" ", strip=True))
        if not text or len(text) > 120:
            continue
        low = text.lower()
        if low in seen:
            continue
        if low in {"remarks", "references", "syntax", "inputs", "outputs", "variables"}:
            continue
        seen.add(low)
        topics.append(text)
        if len(topics) >= limit:
            break
    return topics


def _topic_path(relative_path: str, anchor: str) -> str:
    parts = list(Path(relative_path).parts)
    if anchor not in parts:
        return ""
    anchor_index = parts.index(anchor)
    body_parts = parts[anchor_index + 1 : -1]
    if len(body_parts) <= 1:
        return ""
    return "/".join(body_parts[:-1])


def _split_symbol_title(title: str) -> tuple[str, str]:
    if "::" in title:
        owner, _ = title.split("::", 1)
        return title, owner
    return title, title


def _extract_parameters_from_signature(signature: str, member_name: str) -> tuple[list[dict[str, str]], str]:
    if not signature or not member_name:
        return [], ""

    sanitized = re.sub(r"\b[A-Z_]+\s*\([^)]*\)\s*", "", signature)
    sanitized = _clean(sanitized)
    match = re.search(rf"(.+?)\b{re.escape(member_name)}\s*\((.*)\)", sanitized)
    if not match:
        return [], ""

    returns_text = _clean(match.group(1))
    params_blob = _clean(match.group(2))
    if not params_blob or params_blob == "void":
        return [], returns_text

    params: list[dict[str, str]] = []
    for raw_part in params_blob.split(","):
        part = _clean(raw_part)
        if not part:
            continue
        tokens = part.rsplit(" ", 1)
        if len(tokens) == 2:
            param_type, name = tokens
            params.append({"name": name.strip(), "description": param_type.strip()})
        else:
            params.append({"name": part, "description": ""})
    return params, returns_text


def _extract_pin_table(soup: BeautifulSoup, section_id: str) -> list[dict[str, str]]:
    section = soup.find("div", id=section_id)
    if not section:
        return []
    pins: list[dict[str, str]] = []
    for row in section.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue
        name_cell = cells[1]
        desc_cell = cells[2]
        name_tag = name_cell.find("a")
        name = _clean(name_tag.get_text(" ", strip=True) if name_tag else name_cell.get_text(" ", strip=True))
        type_tag = name_cell.find("div", class_="name-cell-arguments")
        pin_type = _clean(type_tag.get_text(" ", strip=True)) if type_tag else ""
        description = _clean(desc_cell.get_text(" ", strip=True))
        if name:
            pins.append({"name": name, "type": pin_type, "description": description})
    return pins


def _cpp_member_type(title: str, signature: str, refs: dict[str, str], soup: BeautifulSoup) -> str:
    signature_lower = signature.lower()
    title_lower = title.lower()
    headings = {
        _clean(tag.get_text(" ", strip=True)).lower()
        for tag in soup.select("div.heading > p")
    }

    if "enum class " in signature_lower or signature_lower.startswith("enum "):
        return "enum"
    if signature_lower.startswith("struct ") or " struct " in signature_lower:
        return "struct"
    if signature_lower.startswith("class ") or " class " in signature_lower:
        return "class"
    if title.count("::") >= 1 and "(" in signature and ")" in signature:
        return "method"
    if title.count("::") >= 1:
        return "property"
    if any(h.startswith("functions") or h in {"constructors", "variables", "operators"} for h in headings):
        return "class"
    if "module" in refs and "header" not in {k.lower() for k in refs}:
        return "module"
    if "quickstart" in title_lower:
        return "guide"
    return "class" if refs.get("Header") else "module"


def _guide_type(relative_path: str, title: str) -> str:
    lower_path = relative_path.lower()
    lower_title = title.lower()
    if "quickstart" in lower_path or "getting started" in lower_title:
        return "quickstart"
    if "overview" in lower_title:
        return "overview"
    return "reference"


def parse_unreal_cpp_html(html_path: Path, docs_root: Path) -> ApiRecord | GuideRecord:
    relative_path = str(html_path.relative_to(docs_root))

    try:
        raw = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", html_path, exc)
        return GuideRecord(relative_path=relative_path, source_html_path=str(html_path))

    soup = BeautifulSoup(raw, "lxml")
    title = _extract_title(soup)
    summary = _extract_summary(soup, title)
    content_text = _extract_main_text(soup)
    topic_path = _topic_path(relative_path, "API")

    if "/QuickStart/" in relative_path or title.lower().startswith("getting started"):
        topics = _extract_topics(soup)
        return GuideRecord(
            title=title,
            relative_path=relative_path,
            guide_type=_guide_type(relative_path, title),
            topic_path=topic_path,
            summary=summary,
            content_text=content_text,
            key_topics_json=json.dumps(topics, ensure_ascii=False) if topics else "",
            source_html_path=str(html_path),
        )

    refs = _extract_reference_map(soup)
    signature = _extract_code_signature(soup)
    symbol_name, class_name = _split_symbol_title(title)
    member_name = symbol_name.split("::", 1)[1] if "::" in symbol_name else symbol_name
    parameters, returns_text = _extract_parameters_from_signature(signature, member_name)
    member_type = _cpp_member_type(title, signature, refs, soup)
    if member_type == "module":
        class_name = ""
    elif "::" not in symbol_name and member_type not in {"class", "struct", "enum", "interface"}:
        class_name = ""

    hierarchy = _extract_hierarchy(soup)
    remarks = _extract_section_text(soup, "description")
    return ApiRecord(
        title=title,
        relative_path=relative_path,
        symbol_name=symbol_name,
        class_name=class_name,
        namespace="",
        module_name=refs.get("Module", ""),
        topic_path=topic_path,
        member_type=member_type,
        signature=signature,
        parameters_json=json.dumps(parameters, ensure_ascii=False) if parameters else "",
        returns_text=returns_text,
        summary=summary,
        remarks=remarks,
        header_path=refs.get("Header", ""),
        include_text=refs.get("Include", ""),
        source_path=refs.get("Source", ""),
        inheritance_json=json.dumps(hierarchy, ensure_ascii=False) if hierarchy else "",
        content_text=content_text,
        source_html_path=str(html_path),
    )


def parse_blueprint_html(html_path: Path, docs_root: Path) -> ApiRecord:
    relative_path = str(html_path.relative_to(docs_root))

    try:
        raw = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", html_path, exc)
        return ApiRecord(relative_path=relative_path, source_html_path=str(html_path))

    soup = BeautifulSoup(raw, "lxml")
    title = _extract_title(soup)
    summary = _extract_summary(soup, title)
    content_text = _extract_main_text(soup)
    topic_path = _topic_path(relative_path, "BlueprintAPI")
    inputs = _extract_pin_table(soup, "inputs")
    outputs = _extract_pin_table(soup, "outputs")
    node_type = _extract_first_paragraph(soup)
    module_name = topic_path.split("/", 1)[0] if topic_path else ""

    return ApiRecord(
        title=title,
        relative_path=relative_path,
        symbol_name=title,
        class_name="",
        namespace="",
        module_name=module_name,
        topic_path=topic_path,
        member_type="blueprint_node",
        signature=node_type,
        summary=summary,
        inputs_json=json.dumps(inputs, ensure_ascii=False) if inputs else "",
        outputs_json=json.dumps(outputs, ensure_ascii=False) if outputs else "",
        content_text=content_text,
        source_html_path=str(html_path),
    )
