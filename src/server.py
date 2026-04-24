"""MCP server exposing engine/version/docset-aware documentation tools.

This module defines the FastMCP application and all tool handlers.
The server is started via :func:`main` which also triggers an
auto-download of missing databases on startup.

Tool groups
-----------
1. **Search** – keyword (FTS5), semantic (vector), and hybrid search.
2. **Retrieval** – symbol lookups, doc page retrieval, stats.
3. **Navigation** – class hierarchies, member listing, module browsing.
4. **Translation** – cross-engine concept/symbol translation.
5. **Index management** – building/rebuilding indexes and vector stores.
6. **Editor** – live editor interaction (console, scene, objects, play/pause).
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .docsets import docset_status_rows, select_docsets
from .search import (
    IndexNotReadyError,
    answer_question,
    get_doc_page,
    get_stats,
    get_symbol_reference,
    search_api,
    search_guides,
)
from .utils import (
    format_class_info,
    format_class_list,
    format_combined_results,
    format_doc_page,
    format_docset_status,
    format_hybrid_results,
    format_inheritance_chain,
    format_member_list,
    format_module_info,
    format_related_symbols,
    format_search_results,
    format_symbol_ref,
    format_translation_results,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("game-engine-docs-mcp")


def _error_message(exc: Exception) -> str:
    """Format an exception as a user-facing error string."""
    return str(exc).strip() or exc.__class__.__name__


# ===========================================================================
# Search tools
# ===========================================================================


@mcp.tool()
def list_documentation_targets(
    engine: str | None = None,
    version: str | None = None,
) -> str:
    """List registered documentation targets and whether their docs/indexes exist.

    Examples:
      - engine='unity'
      - engine='unreal', version='4.26'
    """

    rows = docset_status_rows(select_docsets(engine=engine, version=version))
    return format_docset_status(rows)


@mcp.tool()
def search_api_reference(
    query: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    limit: int = 10,
    member_type: str | None = None,
) -> str:
    """Search API/reference documentation within a selected engine/version/docset.

    Use this for symbol-style queries such as:
      - Unity: Transform.Rotate, Rigidbody, Quaternion.LookRotation
      - Godot: Node.add_child, CharacterBody3D.move_and_slide, @GlobalScope.print
      - Unreal C++: UCableComponent, UCableComponent::SetAttachEndTo, FTransform
      - Unreal Blueprint: Cast To Actor, Get Actor Location

    Examples:
      - engine='unity'
      - engine='godot', version='4.6', docset='reference'
      - engine='unreal', version='4.26', docset='cpp-api'
      - engine='unreal', version='4.26', docset='blueprint-api'
    """

    try:
        results = search_api(
            query,
            limit=limit,
            member_type=member_type,
            engine=engine,
            version=version,
            docset=docset,
        )
        return format_search_results(results, header=f"API search: '{query}'")
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def search_engine_guides(
    query: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    limit: int = 10,
    guide_type: str | None = None,
) -> str:
    """Search conceptual/guide documentation within a selected engine/version/docset.

    Examples:
      - engine='unity' for Manual pages
      - engine='godot', version='4.6' for class reference overviews, getting-started pages, and manuals
      - engine='unreal', version='4.26', docset='cpp-api' for QuickStart/API overview pages
    """

    try:
        results = search_guides(
            query,
            limit=limit,
            guide_type=guide_type,
            engine=engine,
            version=version,
            docset=docset,
        )
        return format_search_results(results, header=f"Guide search: '{query}'")
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def search_engine_docs(
    query: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    limit: int = 10,
    mode: str = "hybrid",
) -> str:
    """Search documentation using keyword, semantic (vector), or hybrid mode.

    Modes:
      - **keyword** – pure FTS5 BM25 keyword search (fast, exact).
      - **semantic** – vector similarity search (understands meaning).
      - **hybrid** (default) – Reciprocal Rank Fusion of keyword + semantic.

    Use hybrid/semantic for natural language queries like:
      - "how to move a character"
      - "particle effects"
      - "double jump implementation"
    Use keyword for precise symbol lookups.

    Examples:
      - query='how to move character', engine='godot', mode='semantic'
      - query='Transform', engine='unity', mode='keyword'
      - query='spawn enemy', engine='unreal', mode='hybrid'
    """

    try:
        if mode == "keyword":
            bundle = answer_question(
                query, engine=engine, version=version, docset=docset
            )
            return format_combined_results(bundle)

        if mode == "semantic":
            from .vecsearch import vector_search

            results = vector_search(
                query, limit=limit, engine=engine, version=version, docset=docset
            )
            return format_search_results(results, header=f"Semantic search: '{query}'")

        # hybrid (default)
        from .vecsearch import hybrid_search

        results = hybrid_search(
            query, limit=limit, engine=engine, version=version, docset=docset
        )
        return format_hybrid_results(results, query)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)
    except Exception as exc:
        logger.warning("Search failed: %s", exc)
        # Fall back to keyword-only
        try:
            bundle = answer_question(
                query, engine=engine, version=version, docset=docset
            )
            return format_combined_results(bundle)
        except (ValueError, IndexNotReadyError) as exc2:
            return _error_message(exc2)


# ===========================================================================
# Retrieval tools
# ===========================================================================


@mcp.tool()
def get_engine_symbol_reference(
    symbol: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Resolve a single API symbol or Blueprint node to its structured reference.

    Examples:
      - symbol='Transform.Rotate', engine='unity'
      - symbol='Node.add_child', engine='godot', version='4.6'
      - symbol='UCableComponent::SetAttachEndTo', engine='unreal', version='4.26', docset='cpp-api'
    """

    try:
        ref = get_symbol_reference(
            symbol, engine=engine, version=version, docset=docset
        )
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)
    if ref:
        return format_symbol_ref(ref)
    return (
        f"No documentation found for symbol '{symbol}'. "
        "Try search_api_reference for related identifiers or list_documentation_targets "
        "to inspect the available docsets."
    )


@mcp.tool()
def get_engine_doc_page(
    path_or_key: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Retrieve a specific documentation page by relative path or substring.

    Examples:
      - path_or_key='Manual/Transforms.html', engine='unity'
      - path_or_key='classes/class_node.html', engine='godot', version='4.6'
      - path_or_key='API/Runtime/Engine/UCableComponent', engine='unreal', version='4.26', docset='cpp-api'
    """

    try:
        payload = get_doc_page(
            path_or_key, engine=engine, version=version, docset=docset
        )
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)
    if payload:
        return format_doc_page(payload)
    return (
        f"No documentation page found matching '{path_or_key}'. "
        "Try search_api_reference or search_engine_guides to find the correct path."
    )


@mcp.tool()
def answer_engine_question(
    query: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    limit_per_index: int = 5,
) -> str:
    """Run the question against both API/reference and guide indexes."""

    try:
        bundle = answer_question(
            query,
            limit_per_index=limit_per_index,
            engine=engine,
            version=version,
            docset=docset,
        )
        return format_combined_results(bundle)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def get_index_stats(
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Statistics about the selected documentation indexes."""

    try:
        stats = get_stats(engine=engine, version=version, docset=docset)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)

    lines = [
        "Documentation Index Statistics",
        "=" * 30,
        f"Total indexed pages: {stats['total_pages']}",
        f"  - API pages:   {stats['api_pages']}",
        f"  - Guide pages: {stats['guide_pages']}",
        f"Unique classes/types: {stats['unique_classes']}",
        f"Unique namespaces:    {stats['unique_namespaces']}",
        "",
        "Selected docsets:",
    ]
    for row in stats["docsets"]:
        lines.append(
            f"  - {row['label']} ({row['key']}): api={row['api_pages']}, guide={row['guide_pages']}"
        )
    lines += ["", "API member-type breakdown:"]
    for key, value in sorted(
        stats["api_member_breakdown"].items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"  - {key or '(unknown)'}: {value}")
    lines += ["", "Guide-type breakdown:"]
    for key, value in sorted(
        stats["guide_breakdown"].items(), key=lambda item: (-item[1], item[0])
    ):
        lines.append(f"  - {key or '(unknown)'}: {value}")

    # Check vector index status
    try:
        from .vecsearch import _record_exists, _vec_db_path

        vec_dir = _vec_db_path()
        if vec_dir.exists():
            lines += ["", "Vector index:"]
            from .docsets import get_registered_docsets

            for spec in get_registered_docsets():
                status = "yes" if _record_exists(spec) else "no"
                lines.append(f"  - {spec.key}: {status}")
    except Exception:
        pass

    return "\n".join(lines)


# ===========================================================================
# Navigation tools
# ===========================================================================


@mcp.tool()
def browse_class_hierarchy(
    class_name: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Browse a class and its full member listing (methods, properties, signals).

    Returns the class summary, inheritance chain, and all members organized
    by type.

    Examples:
      - class_name='Transform', engine='unity'
      - class_name='Node', engine='godot', version='4.6'
      - class_name='UCableComponent', engine='unreal', version='4.26', docset='cpp-api'
    """

    try:
        from .navigation import browse_class

        info = browse_class(class_name, engine=engine, version=version, docset=docset)
        if info:
            return format_class_info(info)
        return (
            f"Class '{class_name}' not found. "
            "Try search_api_reference to find the correct symbol name."
        )
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def list_class_members(
    class_name: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    member_type: str | None = None,
) -> str:
    """List all members of a class, optionally filtered by member_type (method/property/signal).

    Examples:
      - class_name='Transform', engine='unity', member_type='method'
      - class_name='Node', engine='godot', version='4.6'
      - class_name='AActor', engine='unreal', version='4.26', docset='cpp-api'
    """

    try:
        from .navigation import list_class_members as _list

        members = _list(
            class_name,
            member_type=member_type,
            engine=engine,
            version=version,
            docset=docset,
        )
        return format_member_list(members)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def browse_inheritance_chain(
    class_name: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Show the full inheritance chain for a class (parent -> child order).

    Examples:
      - class_name='Rigidbody', engine='unity'
      - class_name='CharacterBody3D', engine='godot', version='4.6'
      - class_name='ACharacter', engine='unreal', version='4.26', docset='cpp-api'
    """

    try:
        from .navigation import browse_inheritance

        chain = browse_inheritance(
            class_name, engine=engine, version=version, docset=docset
        )
        return format_inheritance_chain(chain)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def list_engine_classes(
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
    prefix: str | None = None,
    limit: int = 50,
) -> str:
    """List all classes in the selected engine/version/docset, optionally filtered by prefix.

    Examples:
      - engine='godot', version='4.6', prefix='Rigid'
      - engine='unity', prefix='Physics'
      - engine='unreal', version='4.26', docset='cpp-api', prefix='U'
    """

    try:
        from .navigation import list_classes

        results = list_classes(
            engine=engine, version=version, docset=docset, prefix=prefix, limit=limit
        )
        return format_class_list(results)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def browse_module(
    module_name: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Browse a module or namespace, showing its classes and total member count.

    Examples:
      - module_name='CableComponent', engine='unreal', version='4.26'
      - module_name='UnityEngine', engine='unity'
    """

    try:
        from .navigation import browse_module as _browse

        info = _browse(module_name, engine=engine, version=version, docset=docset)
        if info:
            return format_module_info(info)
        return f"Module '{module_name}' not found in the selected docsets."
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def get_related_symbols(
    symbol: str,
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Find symbols related to the given one (same class, same topic/module).

    Examples:
      - symbol='Transform.Rotate', engine='unity'
      - symbol='Node.add_child', engine='godot', version='4.6'
    """

    try:
        from .navigation import get_related_symbols as _get

        results = _get(symbol, engine=engine, version=version, docset=docset)
        return format_related_symbols(results)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


# ===========================================================================
# Cross-engine translation tools
# ===========================================================================


@mcp.tool()
def translate_symbol(
    symbol: str,
    source_engine: str,
    target_engine: str,
) -> str:
    """Find the equivalent of a symbol/concept in a different game engine.

    Uses concept mapping and fuzzy name matching to find corresponding APIs
    across Unity, Godot, and Unreal Engine.

    Examples:
      - symbol='Rigidbody', source_engine='unity', target_engine='godot'
      - symbol='Node.add_child', source_engine='godot', target_engine='unreal'
      - symbol='AActor', source_engine='unreal', target_engine='unity'
    """

    try:
        from .crossengine import translate_symbol as _translate

        results = _translate(symbol, source_engine, target_engine)
        return format_translation_results(results, symbol, source_engine, target_engine)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


@mcp.tool()
def compare_across_engines(
    symbol: str,
) -> str:
    """Look up a symbol across all indexed engines and show equivalents.

    Automatically detects the source engine and finds matches in the others.

    Examples:
      - symbol='Transform'
      - symbol='Rigidbody'
      - symbol='Camera'
    """

    try:
        from .crossengine import compare_symbol_across_engines

        results = compare_symbol_across_engines(symbol)
        if not results:
            return f"No cross-engine equivalents found for '{symbol}'."

        parts = [f"Cross-engine comparison: '{symbol}'", "=" * 35]
        for target_engine, hits in results.items():
            parts.append(f"\n## {target_engine.title()}")
            if not hits:
                parts.append("  No equivalent found.")
            for hit in hits:
                conf = {"high": "HIGH", "medium": "MED", "low": "LOW"}.get(
                    hit.confidence, hit.confidence
                )
                parts.append(
                    f"  [{conf}] {hit.target_symbol} — {hit.target_summary or hit.target_title}"
                )
        return "\n".join(parts)
    except (ValueError, IndexNotReadyError) as exc:
        return _error_message(exc)


# ===========================================================================
# Index management tools
# ===========================================================================


@mcp.tool()
def build_vector_index(
    engine: str | None = None,
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Build (or rebuild) the vector search index from the existing SQLite index.

    This embeds all API and guide records using a local sentence-transformer
    model and stores the vectors in a LanceDB sidecar for semantic search.

    Must be run after the base SQLite index is built.  This can take a few
    minutes for large docsets.
    """

    try:
        from .vecsearch import build_vector_index
        from .docsets import select_docsets

        specs = select_docsets(engine=engine, version=version, docset=docset)
        indexed = [s for s in specs if s.indexed]
        if not indexed:
            return "No indexed docsets found. Build the SQLite index first."

        results = []
        for spec in indexed:
            stats = build_vector_index(spec)
            results.append(
                f"  {spec.key}: api={stats['api_embedded']}, guide={stats['guide_embedded']}, "
                f"time={stats['elapsed_seconds']}s"
            )
        return "Vector index built:\n" + "\n".join(results)
    except Exception as exc:
        return f"Error building vector index: {exc}"


# ===========================================================================
# Backwards-compatible Unity wrappers
# ===========================================================================


# ---------------------------------------------------------------------------
# Backwards-compatible Unity wrappers
# ---------------------------------------------------------------------------


@mcp.tool()
def search_unity_api(
    query: str, limit: int = 10, member_type: str | None = None
) -> str:
    """Compatibility wrapper around search_api_reference(engine='unity')."""

    return search_api_reference(
        query=query,
        engine="unity",
        limit=limit,
        member_type=member_type,
    )


@mcp.tool()
def search_unity_guides(
    query: str, limit: int = 10, guide_type: str | None = None
) -> str:
    """Compatibility wrapper around search_engine_guides(engine='unity')."""

    return search_engine_guides(
        query=query,
        engine="unity",
        limit=limit,
        guide_type=guide_type,
    )


@mcp.tool()
def get_unity_symbol_reference(symbol: str) -> str:
    """Compatibility wrapper around get_engine_symbol_reference(engine='unity')."""

    return get_engine_symbol_reference(symbol=symbol, engine="unity")


@mcp.tool()
def get_unity_doc_page(path_or_key: str) -> str:
    """Compatibility wrapper around get_engine_doc_page(engine='unity')."""

    return get_engine_doc_page(path_or_key=path_or_key, engine="unity")


@mcp.tool()
def answer_unity_question(query: str, limit_per_index: int = 5) -> str:
    """Compatibility wrapper around answer_engine_question(engine='unity')."""

    return answer_engine_question(
        query=query,
        engine="unity",
        limit_per_index=limit_per_index,
    )


@mcp.tool()
def get_unity_index_stats() -> str:
    """Compatibility wrapper around get_index_stats(engine='unity')."""

    return get_index_stats(engine="unity")


def main() -> None:
    """Entry point: configure logging, auto-download databases, start the MCP server."""
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Auto-download missing databases from GitHub Releases
    try:
        from .downloader import ensure_databases

        ensure_databases()
    except FileNotFoundError:
        logger.warning("No config.yaml found — skipping auto-download")
    except Exception as exc:
        logger.warning("Auto-download failed: %s", exc)

    # Register live editor tools
    try:
        from .editor_tools import register_editor_tools

        register_editor_tools(mcp)
    except Exception as exc:
        logger.warning("Editor tools registration failed: %s", exc)

    # Auto-connect bridges if configured
    try:
        from .bridge_config import load_bridge_config
        from .bridges.registry import BridgeRegistry

        config = load_bridge_config()
        asyncio.run(BridgeRegistry.instance().auto_connect(config))
    except Exception as exc:
        logger.warning("Bridge auto-connect failed: %s", exc)

    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    if "--stdio" in sys.argv:
        transport = "stdio"
    elif "--sse" in sys.argv:
        transport = "sse"

    if transport in ("streamable-http", "sse"):
        host = (
            os.environ.get("GAME_DOCS_MCP_HOST")
            or os.environ.get("UNITY_MCP_HOST")
            or "0.0.0.0"
        )
        port = int(
            os.environ.get("GAME_DOCS_MCP_PORT")
            or os.environ.get("UNITY_MCP_PORT")
            or "8080"
        )
        for arg in sys.argv:
            if arg.startswith("--host="):
                host = arg.split("=", 1)[1]
            elif arg.startswith("--port="):
                port = int(arg.split("=", 1)[1])
        mcp.settings.host = host
        mcp.settings.port = port

    print(
        f"Documentation MCP server starting (transport={transport}) on http://{host}:{port}",
        file=sys.stderr,
    )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
