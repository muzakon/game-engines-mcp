"""Unity offline HTML parser.

Extracts API records (classes, methods, properties) from Unity
ScriptReference pages and guide records from Manual pages.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag

from ..models import ApiRecord, GuideRecord

logger = logging.getLogger(__name__)

_MANUAL_CLASS_PAGE_RE = re.compile(r"^class-[A-Z]", re.IGNORECASE)
_NAMESPACE_RE = re.compile(
    r"(?:class|struct|enum|interface|delegate)\s+in\s+([\w.]+)",
    re.IGNORECASE,
)


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _strip_chrome(content_div: Tag) -> None:
    for tag in content_div.find_all(["script", "style", "nav", "form", "noscript"]):
        tag.decompose()
    for cls in (
        "suggest",
        "scrollToFeedback",
        "footer-wrapper",
        "header-wrapper",
        "toolbar",
        "breadcrumbs",
        "sidebar",
        "version-selector",
    ):
        for tag in content_div.find_all(attrs={"class": cls}):
            tag.decompose()


def _main_content_div(soup: BeautifulSoup) -> Tag:
    return (
        soup.find("div", id="content-wrap")
        or soup.find("div", class_="content-wrap")
        or soup.find("div", id="docs-content")
        or soup.find("body")
        or soup
    )


def classify_page(relative_path: str, soup: BeautifulSoup) -> str:
    """Return 'api' or 'guide'."""

    marker = soup.find("div", id="DocsAnalyticsData")
    if marker is not None:
        page_type = marker.get("data-pagetype", "").lower()
        if page_type == "scriptref":
            return "api"
        if page_type in {"manual", "guide", "tutorial"}:
            return "guide"

    if "ScriptReference" in relative_path:
        return "api"
    if "Manual" in relative_path:
        return "guide"
    if soup.find("div", class_="signature") or soup.find("div", class_="sig-block"):
        return "api"
    return "guide"


def guide_type_for(relative_path: str, title: str) -> str:
    path_lower = relative_path.lower()
    title_lower = title.lower()

    if _MANUAL_CLASS_PAGE_RE.match(Path(relative_path).stem or ""):
        return "reference"
    if any(
        kw in path_lower
        for kw in ("tutorial", "gettingstarted", "getting-started", "quickstart")
    ):
        return "tutorial"
    if any(kw in title_lower for kw in ("getting started", "quick start", "tutorial")):
        return "tutorial"
    if any(kw in title_lower for kw in ("overview", "introduction")):
        return "overview"
    if "/Manual/" in relative_path or relative_path.startswith("en/Manual/"):
        return "manual"
    return "general"


def _topic_path(relative_path: str) -> str:
    parts = Path(relative_path).parts
    if len(parts) <= 2:
        return ""
    return "/".join(parts[1:-1])


def _extract_title(soup: BeautifulSoup) -> str:
    tag = soup.find("title")
    if tag:
        raw = tag.get_text()
        cleaned = raw.replace("Unity - Scripting API:", "").replace(
            "Unity - Manual:", ""
        )
        return _clean(cleaned)
    h1 = soup.find("h1")
    return _clean(h1.get_text()) if h1 else ""


def _extract_main_text(soup: BeautifulSoup) -> str:
    content_div = _main_content_div(soup)
    _strip_chrome(content_div)
    return _clean(content_div.get_text(separator=" ", strip=True))


def _extract_summary(soup: BeautifulSoup) -> str:
    for subsection in soup.find_all("div", class_="subsection"):
        h3 = subsection.find("h3")
        if h3 and "description" in h3.get_text(strip=True).lower():
            p = subsection.find("p")
            if p:
                text = _clean(p.get_text())
                if text:
                    return text[:800]

    content_div = _main_content_div(soup)
    for p in content_div.find_all("p"):
        text = _clean(p.get_text())
        if len(text) > 20:
            return text[:500]
    return ""


def _extract_signatures(soup: BeautifulSoup) -> list[str]:
    sigs: list[str] = []
    for sig_div in soup.find_all("div", class_="signature"):
        for block in sig_div.find_all("div", class_="sig-block"):
            text = _clean(block.get_text(separator=" ", strip=True))
            text = re.sub(r"^Declaration\s*", "", text)
            if text:
                sigs.append(text)
    return sigs


def _extract_subsection_text(
    soup: BeautifulSoup, heading_keywords: tuple[str, ...]
) -> str:
    for subsection in soup.find_all("div", class_="subsection"):
        h3 = subsection.find("h3")
        if not h3:
            continue
        heading = h3.get_text(strip=True).lower()
        if any(kw in heading for kw in heading_keywords):
            parts = [_clean(p.get_text()) for p in subsection.find_all("p")]
            joined = " ".join(p for p in parts if p)
            if joined:
                return joined[:2000]
    return ""


def _extract_parameters(soup: BeautifulSoup) -> list[dict[str, str]]:
    params: list[dict[str, str]] = []
    for subsection in soup.find_all("div", class_="subsection"):
        h3 = subsection.find("h3")
        if not h3 or "parameter" not in h3.get_text(strip=True).lower():
            continue
        table = subsection.find("table", class_="list") or subsection.find("table")
        if not table:
            continue
        for row in table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                name = _clean(cells[0].get_text())
                desc = _clean(cells[1].get_text())
                if name and name.lower() not in ("parameter", "property", "function"):
                    params.append({"name": name, "description": desc})
    return params


def _infer_member_type(
    relative_path: str, title: str, signature: str, content: str
) -> str:
    stem = Path(relative_path).stem

    if "-" in stem and not stem.startswith("-"):
        low = content[:800].lower()
        if (
            "event " in signature.lower()
            or "add_" in signature.lower()
            or "event" in stem.lower()
        ):
            return "event"
        if "readonly" in signature.lower() or "get;" in signature:
            return "property"
        if "{ get" in signature or "}" in signature or "get;" in signature:
            return "property"
        if (
            "public static readonly" in signature.lower()
            or "const " in signature.lower()
        ):
            return "field"
        if "field" in low:
            return "field"
        return "property"

    head = content[:300].lower()
    if "struct in " in head:
        return "struct"
    if "enum in " in head:
        return "enum"
    if "interface in " in head:
        return "interface"
    if "delegate in " in head:
        return "delegate"
    if "class in " in head:
        return "class"

    if "." in stem and (
        "(" in signature
        or "void " in signature.lower()
        or "returns " in content.lower()
    ):
        return "method"
    if "." in title and signature:
        return "method"
    return "class"


def _parse_symbol_from_title(title: str) -> tuple[str, str]:
    title = title.strip()
    if not title:
        return "", ""
    if "." in title:
        class_name = title.split(".", 1)[0].strip()
        return title, class_name
    return title, title


def _extract_key_topics(soup: BeautifulSoup, limit: int = 20) -> list[str]:
    topics: list[str] = []
    seen: set[str] = set()
    content_div = _main_content_div(soup)
    for tag in content_div.find_all(["h2", "h3", "h4"]):
        text = _clean(tag.get_text())
        if not text or len(text) > 120:
            continue
        low = text.lower()
        if low in seen:
            continue
        if low in {
            "description",
            "parameters",
            "returns",
            "remarks",
            "leave feedback",
            "success!",
        }:
            continue
        seen.add(low)
        topics.append(text)
        if len(topics) >= limit:
            break
    return topics


def parse_unity_html(html_path: Path, docs_root: Path) -> ApiRecord | GuideRecord:
    relative_path = str(html_path.relative_to(docs_root))

    try:
        raw = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        logger.warning("Failed to read %s: %s", html_path, exc)
        return GuideRecord(relative_path=relative_path, source_html_path=str(html_path))

    soup = BeautifulSoup(raw, "lxml")
    category = classify_page(relative_path, soup)
    title = _extract_title(soup)
    topic_path = _topic_path(relative_path)

    if category == "api":
        content_text = _extract_main_text(soup)
        summary = _extract_summary(soup)
        signatures = _extract_signatures(soup)
        signature = "\n".join(signatures) if signatures else ""
        params = _extract_parameters(soup)
        parameters_json = json.dumps(params, ensure_ascii=False) if params else ""
        returns_text = _extract_subsection_text(soup, ("return",))
        remarks = _extract_subsection_text(soup, ("remark", "note"))
        symbol_name, class_name = _parse_symbol_from_title(title)

        namespace = ""
        ns_match = _NAMESPACE_RE.search(content_text)
        if ns_match:
            namespace = ns_match.group(1)

        member_type = _infer_member_type(relative_path, title, signature, content_text)
        return ApiRecord(
            title=title,
            relative_path=relative_path,
            symbol_name=symbol_name,
            class_name=class_name,
            namespace=namespace,
            member_type=member_type,
            signature=signature,
            parameters_json=parameters_json,
            returns_text=returns_text,
            summary=summary,
            remarks=remarks,
            topic_path=topic_path,
            content_text=content_text,
            source_html_path=str(html_path),
        )

    content_text = _extract_main_text(soup)
    summary = _extract_summary(soup)
    topics = _extract_key_topics(soup)
    key_topics_json = json.dumps(topics, ensure_ascii=False) if topics else ""
    return GuideRecord(
        title=title,
        relative_path=relative_path,
        guide_type=guide_type_for(relative_path, title),
        topic_path=topic_path,
        summary=summary,
        content_text=content_text,
        key_topics_json=key_topics_json,
        source_html_path=str(html_path),
    )
