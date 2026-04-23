"""Structural navigation over indexed documentation.

Provides tools for browsing class hierarchies, listing members, and
exploring modules/namespaces -- all powered by the existing SQLite index.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from .db import get_connection
from .docsets import DocsetSpec, select_docsets
from .search import IndexNotReadyError

logger = logging.getLogger(__name__)


@dataclass
class ClassInfo:
    """Summary of a class with its direct members."""

    symbol_name: str
    title: str
    member_type: str
    summary: str
    relative_path: str
    engine: str
    version: str
    docset: str
    docset_label: str
    inheritance: list[str]
    methods: list[dict]
    properties: list[dict]
    signals: list[dict]
    other_members: list[dict]


@dataclass
class ModuleInfo:
    """Summary of a module or namespace."""

    name: str
    engine: str
    version: str
    docset: str
    docset_label: str
    classes: list[str]
    total_members: int


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def browse_class(
    class_name: str,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> ClassInfo | None:
    """Look up a class and return its full member listing.

    Returns ``None`` if no matching class is found.
    """
    specs = _resolve_specs(engine=engine, version=version, docset=docset)

    for spec in specs:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            # Find the class record itself
            class_row = conn.execute(
                """
                SELECT * FROM api_records
                WHERE (symbol_name = ? COLLATE NOCASE OR class_name = ? COLLATE NOCASE)
                  AND member_type IN ('class', '')
                LIMIT 1
                """,
                (class_name, class_name),
            ).fetchone()
            if not class_row:
                continue

            # Gather all members of this class
            members = conn.execute(
                """
                SELECT symbol_name, title, member_type, signature, summary, relative_path
                FROM api_records
                WHERE class_name = ? COLLATE NOCASE
                  AND member_type != 'class'
                ORDER BY member_type, symbol_name
                """,
                (class_row["symbol_name"] or class_row["class_name"],),
            ).fetchall()

            methods = []
            properties = []
            signals = []
            other = []
            for m in members:
                entry = {
                    "symbol_name": m["symbol_name"],
                    "title": m["title"],
                    "signature": m["signature"],
                    "summary": m["summary"],
                    "relative_path": m["relative_path"],
                }
                mt = (m["member_type"] or "").lower()
                if mt == "method":
                    methods.append(entry)
                elif mt in ("property", "variable", "field"):
                    properties.append(entry)
                elif mt == "signal":
                    signals.append(entry)
                else:
                    other.append(entry)

            inheritance = []
            inh_json = class_row["inheritance_json"]
            if inh_json:
                try:
                    inheritance = json.loads(inh_json)
                except (json.JSONDecodeError, TypeError):
                    pass

            return ClassInfo(
                symbol_name=class_row["symbol_name"] or class_row["class_name"],
                title=class_row["title"],
                member_type=class_row["member_type"],
                summary=class_row["summary"],
                relative_path=class_row["relative_path"],
                engine=spec.engine,
                version=spec.version,
                docset=spec.docset,
                docset_label=spec.label,
                inheritance=inheritance,
                methods=methods,
                properties=properties,
                signals=signals,
                other_members=other,
            )
        finally:
            conn.close()

    return None


def list_class_members(
    class_name: str,
    *,
    member_type: str | None = None,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> list[dict]:
    """List all members of a class, optionally filtered by member type.

    Returns a list of dicts with keys ``symbol_name``, ``title``,
    ``member_type``, ``signature``, ``summary``, ``relative_path``.
    """
    specs = _resolve_specs(engine=engine, version=version, docset=docset)
    results: list[dict] = []

    for spec in specs:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            # Resolve the actual class name
            class_row = conn.execute(
                """
                SELECT symbol_name, class_name FROM api_records
                WHERE (symbol_name = ? COLLATE NOCASE OR class_name = ? COLLATE NOCASE)
                  AND member_type IN ('class', '')
                LIMIT 1
                """,
                (class_name, class_name),
            ).fetchone()
            if not class_row:
                continue

            resolved_class = class_row["symbol_name"] or class_row["class_name"]

            type_clause = " AND member_type = ? " if member_type else ""
            type_args = (member_type,) if member_type else ()

            rows = conn.execute(
                f"""
                SELECT symbol_name, title, member_type, signature, summary, relative_path
                FROM api_records
                WHERE class_name = ? COLLATE NOCASE
                  AND member_type != 'class'
                  {type_clause}
                ORDER BY member_type, symbol_name
                """,
                (resolved_class, *type_args),
            ).fetchall()

            results.extend(dict(row) for row in rows)
        finally:
            conn.close()

    return results


def browse_inheritance(
    class_name: str,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> list[dict]:
    """Return the inheritance chain for a class.

    Each entry has ``symbol_name``, ``title``, ``relative_path``, and ``summary``.
    """
    specs = _resolve_specs(engine=engine, version=version, docset=docset)
    chain: list[dict] = []
    seen: set[str] = set()

    for spec in specs:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            current = class_name
            for _ in range(20):  # safety limit
                if current.lower() in seen:
                    break
                seen.add(current.lower())

                row = conn.execute(
                    """
                    SELECT symbol_name, title, relative_path, summary, inheritance_json, class_name
                    FROM api_records
                    WHERE (symbol_name = ? COLLATE NOCASE OR class_name = ? COLLATE NOCASE)
                      AND member_type IN ('class', '')
                    LIMIT 1
                    """,
                    (current, current),
                ).fetchone()
                if not row:
                    break

                chain.append(
                    {
                        "symbol_name": row["symbol_name"] or row["class_name"],
                        "title": row["title"],
                        "relative_path": row["relative_path"],
                        "summary": row["summary"],
                        "engine": spec.engine,
                        "version": spec.version,
                        "docset": spec.docset,
                    }
                )

                # Walk up the inheritance
                inh_json = row["inheritance_json"]
                if not inh_json:
                    break
                try:
                    parents = json.loads(inh_json)
                except (json.JSONDecodeError, TypeError):
                    break
                if len(parents) < 2:
                    break
                current = parents[1]  # parents[0] is the class itself
        finally:
            conn.close()

    return chain


def list_classes(
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    prefix: str | None = None,
    limit: int = 50,
) -> list[dict]:
    """List all classes across selected docsets, optionally filtered by prefix.

    Returns a list of dicts with ``symbol_name``, ``class_name``,
    ``summary``, ``relative_path``.
    """
    specs = _resolve_specs(engine=engine, version=version, docset=docset)
    results: list[dict] = []

    for spec in specs:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            prefix_clause = " AND symbol_name LIKE ? " if prefix else ""
            prefix_args = (f"{prefix}%",) if prefix else ()

            rows = conn.execute(
                f"""
                SELECT symbol_name, class_name, summary, relative_path
                FROM api_records
                WHERE member_type = 'class'
                  {prefix_clause}
                ORDER BY symbol_name
                LIMIT ?
                """,
                (*prefix_args, limit),
            ).fetchall()
            results.extend(
                {
                    "symbol_name": row["symbol_name"],
                    "class_name": row["class_name"],
                    "summary": row["summary"],
                    "relative_path": row["relative_path"],
                    "engine": spec.engine,
                    "version": spec.version,
                    "docset": spec.docset,
                }
                for row in rows
            )
        finally:
            conn.close()

    return results


def browse_module(
    module_name: str,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> ModuleInfo | None:
    """Browse a module or namespace, returning its classes and stats."""
    specs = _resolve_specs(engine=engine, version=version, docset=docset)

    for spec in specs:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            # Check if any records exist in this module
            count = conn.execute(
                """
                SELECT COUNT(*) FROM api_records
                WHERE module_name = ? COLLATE NOCASE
                   OR namespace = ? COLLATE NOCASE
                """,
                (module_name, module_name),
            ).fetchone()[0]
            if count == 0:
                continue

            classes = [
                row[0]
                for row in conn.execute(
                    """
                    SELECT DISTINCT COALESCE(symbol_name, class_name)
                    FROM api_records
                    WHERE (module_name = ? COLLATE NOCASE OR namespace = ? COLLATE NOCASE)
                      AND member_type = 'class'
                    ORDER BY 1
                    """,
                    (module_name, module_name),
                ).fetchall()
            ]

            return ModuleInfo(
                name=module_name,
                engine=spec.engine,
                version=spec.version,
                docset=spec.docset,
                docset_label=spec.label,
                classes=classes,
                total_members=count,
            )
        finally:
            conn.close()

    return None


def get_related_symbols(
    symbol: str,
    *,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Find symbols related to the given one (same class, same module, etc.)."""
    specs = _resolve_specs(engine=engine, version=version, docset=docset)
    results: list[dict] = []

    for spec in specs:
        conn = get_connection(spec.db_path, readonly=True)
        try:
            # Find the source record
            source = conn.execute(
                """
                SELECT class_name, module_name, namespace, topic_path
                FROM api_records
                WHERE symbol_name = ? COLLATE NOCASE
                   OR title = ? COLLATE NOCASE
                LIMIT 1
                """,
                (symbol, symbol),
            ).fetchone()
            if not source:
                continue

            # Find related: same class, or same topic_path
            rows = conn.execute(
                """
                SELECT symbol_name, title, member_type, summary, relative_path
                FROM api_records
                WHERE (
                    class_name = ? AND class_name != ''
                    OR topic_path = ? AND topic_path != ''
                )
                AND symbol_name != ? COLLATE NOCASE
                ORDER BY
                    CASE WHEN class_name = ? THEN 0 ELSE 1 END,
                    member_type, symbol_name
                LIMIT ?
                """,
                (
                    source["class_name"],
                    source["topic_path"],
                    symbol,
                    source["class_name"],
                    limit,
                ),
            ).fetchall()

            results.extend(
                {
                    "symbol_name": row["symbol_name"],
                    "title": row["title"],
                    "member_type": row["member_type"],
                    "summary": row["summary"],
                    "relative_path": row["relative_path"],
                    "engine": spec.engine,
                    "version": spec.version,
                    "docset": spec.docset,
                }
                for row in rows
            )
        finally:
            conn.close()

    return results[:limit]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _resolve_specs(
    *,
    engine: str | None,
    version: str | None,
    docset: str | None,
) -> list[DocsetSpec]:
    """Select indexed docsets, raising on empty."""
    specs = select_docsets(engine=engine, version=version, docset=docset)
    if not specs:
        raise ValueError("No matching documentation targets were found.")

    indexed = [s for s in specs if s.indexed]
    if indexed:
        return indexed

    labels = ", ".join(s.key for s in specs)
    raise IndexNotReadyError(
        f"No index database is available for the selected docset(s): {labels}. "
        "Build the index first with scripts/build_index.py."
    )
