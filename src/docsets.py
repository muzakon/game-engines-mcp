"""Docset registry, manifest loading, and selection helpers.

A *docset* (documentation set) is identified by the triple
``engine:version:docset`` (e.g. ``unreal:4.26:cpp-api``).  Docset
specifications can come from three sources, in priority order:

1. ``engines.local.yaml`` – user-specific engine preferences.
2. A custom JSON manifest path (via argument or ``UNITY_MCP_DOCSETS_MANIFEST``).
3. ``docsets.json`` – the default manifest shipped with the repo.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path
from typing import Iterable

import yaml

from .config import (
    DATA_DIR,
    DOCSETS_MANIFEST_PATH,
    PROJECT_ROOT,
)

logger = logging.getLogger(__name__)

# Default parser_kind per engine (and optionally per docset within an engine).
_DEFAULT_PARSER_KINDS: dict[str, str] = {
    "godot": "godot_html",
    "unity": "unity_html",
    "unreal": "unreal_cpp_html",
}

_UNREAL_DOCSET_PARSER_OVERRIDES: dict[str, str] = {
    "cpp-api": "unreal_cpp_html",
    "blueprint-api": "unreal_blueprint_html",
}

_CONFIG_YAML_PATH = PROJECT_ROOT / "config.yaml"
_ENGINES_LOCAL_PATH = PROJECT_ROOT / "engines.local.yaml"


def _default_parser_kind(engine: str, docset: str) -> str:
    """Return the parser kind for an engine/docset combination."""
    if engine == "unreal":
        return _UNREAL_DOCSET_PARSER_OVERRIDES.get(docset, "unreal_cpp_html")
    return _DEFAULT_PARSER_KINDS.get(engine, "unknown")


def _normalize(value: str | None) -> str | None:
    """Lowercase and strip whitespace, returning *None* for empty strings."""
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned.lower() if cleaned else None


def _resolve_path(value: str | None, fallback: Path) -> Path:
    """Resolve a path string relative to ``PROJECT_ROOT`` if not absolute."""
    if not value:
        return fallback
    path = Path(value)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


@dataclass(frozen=True)
class DocsetSpec:
    """A single searchable documentation target."""

    engine: str
    version: str
    docset: str
    label: str
    docs_root: Path
    db_path: Path
    parser_kind: str
    description: str = ""
    skip_dirs: tuple[str, ...] = ()
    include_in_default_build: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "engine", self.engine.strip().lower())
        object.__setattr__(self, "version", self.version.strip())
        object.__setattr__(self, "docset", self.docset.strip().lower())
        object.__setattr__(self, "docs_root", Path(self.docs_root))
        object.__setattr__(self, "db_path", Path(self.db_path))
        object.__setattr__(self, "skip_dirs", tuple(self.skip_dirs))

    @property
    def key(self) -> str:
        return f"{self.engine}:{self.version}:{self.docset}"

    @property
    def available(self) -> bool:
        return self.docs_root.exists()

    @property
    def indexed(self) -> bool:
        return self.db_path.exists()

    def with_overrides(
        self,
        docs_root: Path | None = None,
        db_path: Path | None = None,
    ) -> "DocsetSpec":
        return replace(
            self,
            docs_root=docs_root or self.docs_root,
            db_path=db_path or self.db_path,
        )


def default_manifest_path() -> Path:
    """Return the default manifest path, honouring the env override."""
    raw = os.environ.get("UNITY_MCP_DOCSETS_MANIFEST")
    return Path(raw) if raw else DOCSETS_MANIFEST_PATH


@lru_cache(maxsize=8)
def _load_manifest_cached(manifest_path_str: str) -> tuple[DocsetSpec, ...]:
    """Load and cache a JSON manifest file."""
    manifest_path = Path(manifest_path_str)
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Docset manifest must be a JSON list: {manifest_path}")

    docsets: list[DocsetSpec] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ValueError(f"Invalid docset entry in {manifest_path}: {item!r}")
        engine = str(item["engine"])
        version = str(item["version"])
        docset = str(item["docset"])
        default_db = DATA_DIR / engine.lower() / version / f"{docset.lower()}.db"
        default_docs_root = PROJECT_ROOT / "docs" / engine.lower() / version / docset.lower()
        spec = DocsetSpec(
            engine=engine,
            version=version,
            docset=docset,
            label=str(item.get("label") or f"{engine} {version} {docset}"),
            description=str(item.get("description", "")),
            docs_root=_resolve_path(item.get("docs_root"), default_docs_root),
            db_path=_resolve_path(item.get("db_path"), default_db),
            parser_kind=str(item["parser_kind"]),
            skip_dirs=tuple(str(x) for x in item.get("skip_dirs", ())),
            include_in_default_build=bool(item.get("include_in_default_build", True)),
        )
        docsets.append(spec)

    return tuple(sorted(docsets, key=lambda spec: (spec.engine, spec.version, spec.docset)))


def _load_from_config_yaml() -> tuple[DocsetSpec, ...] | None:
    """Load docsets from ``engines.local.yaml``, or *None* if it doesn't exist."""
    if not _ENGINES_LOCAL_PATH.exists():
        return None

    with open(_ENGINES_LOCAL_PATH, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not raw or "engines" not in raw:
        return None

    docsets: list[DocsetSpec] = []
    for entry in raw["engines"]:
        engine = str(entry["engine"]).strip().lower()
        version = str(entry["version"]).strip()
        for docset_name in entry.get("docsets", ["reference"]):
            docset_name = docset_name.strip().lower()
            default_db = DATA_DIR / engine / version / f"{docset_name}.db"
            default_docs_root = PROJECT_ROOT / "docs" / engine / version / docset_name
            spec = DocsetSpec(
                engine=engine,
                version=version,
                docset=docset_name,
                label=f"{engine.title()} {version} {docset_name}",
                docs_root=default_docs_root,
                db_path=default_db,
                parser_kind=_default_parser_kind(engine, docset_name),
            )
            docsets.append(spec)

    logger.info("Loaded %d docset(s) from engines.local.yaml", len(docsets))
    return tuple(sorted(docsets, key=lambda spec: (spec.engine, spec.version, spec.docset)))


def clear_docset_cache() -> None:
    """Invalidate the cached manifest (used between tests)."""
    _load_manifest_cached.cache_clear()


def get_registered_docsets(manifest_path: Path | None = None) -> tuple[DocsetSpec, ...]:
    """Return all registered docsets using the standard resolution order.

    Priority: custom manifest > ``engines.local.yaml`` > ``docsets.json``.
    """
    # If a custom manifest is explicitly requested (via arg or env var), use that
    explicit = manifest_path or os.environ.get("UNITY_MCP_DOCSETS_MANIFEST")
    if explicit:
        return _load_manifest_cached(str(Path(explicit).resolve()))

    # Otherwise prefer engines.local.yaml when it exists
    from_config = _load_from_config_yaml()
    if from_config is not None:
        return from_config

    # Fall back to docsets.json manifest
    path = default_manifest_path()
    return _load_manifest_cached(str(path.resolve()))


def _matches(spec: DocsetSpec, engine: str | None, version: str | None, docset: str | None) -> bool:
    """Check whether a spec matches the given filter criteria."""
    if engine and spec.engine != engine:
        return False
    if version and spec.version.lower() != version.lower():
        return False
    if docset and spec.docset != docset:
        return False
    return True


def select_docsets(
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    *,
    available_only: bool = False,
    indexed_only: bool = False,
    manifest_path: Path | None = None,
) -> list[DocsetSpec]:
    """Filter registered docsets by engine/version/docset."""

    engine = _normalize(engine)
    docset = _normalize(docset)

    if docset and not engine and not version and docset.count(":") == 2:
        engine, version, docset = docset.split(":", 2)
        engine = _normalize(engine)
        docset = _normalize(docset)

    matches: list[DocsetSpec] = []
    for spec in get_registered_docsets(manifest_path):
        if not _matches(spec, engine, version, docset):
            continue
        if available_only and not spec.available:
            continue
        if indexed_only and not spec.indexed:
            continue
        matches.append(spec)
    return matches


def get_docset(
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    *,
    available_only: bool = False,
    indexed_only: bool = False,
    manifest_path: Path | None = None,
) -> DocsetSpec:
    """Resolve a single docset or raise if the selection is ambiguous."""

    matches = select_docsets(
        engine=engine,
        version=version,
        docset=docset,
        available_only=available_only,
        indexed_only=indexed_only,
        manifest_path=manifest_path,
    )
    if not matches:
        selection = ", ".join(
            part for part in (
                f"engine={engine!r}" if engine else "",
                f"version={version!r}" if version else "",
                f"docset={docset!r}" if docset else "",
            )
            if part
        ) or "default selection"
        raise ValueError(f"No docset matched {selection}.")
    if len(matches) > 1:
        labels = ", ".join(spec.key for spec in matches)
        raise ValueError(f"Selection is ambiguous. Matching docsets: {labels}")
    return matches[0]


def describe_docset(spec: DocsetSpec) -> str:
    """Return a human-readable label for a docset."""
    return f"{spec.label} ({spec.key})"


def docset_status_rows(docsets: Iterable[DocsetSpec]) -> list[dict[str, str | bool]]:
    """Convert docset specs into flat status dicts for formatting."""
    rows: list[dict[str, str | bool]] = []
    for spec in docsets:
        rows.append(
            {
                "key": spec.key,
                "label": spec.label,
                "engine": spec.engine,
                "version": spec.version,
                "docset": spec.docset,
                "docs_root": str(spec.docs_root),
                "db_path": str(spec.db_path),
                "parser_kind": spec.parser_kind,
                "description": spec.description,
                "docs_available": spec.available,
                "index_available": spec.indexed,
            }
        )
    return rows
