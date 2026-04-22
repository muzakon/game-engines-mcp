"""MCP server exposing engine/version/docset-aware documentation tools."""

from __future__ import annotations

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
    format_combined_results,
    format_doc_page,
    format_docset_status,
    format_search_results,
    format_symbol_ref,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("game-engine-docs-mcp")


def _error_message(exc: Exception) -> str:
    return str(exc).strip() or exc.__class__.__name__


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
    engine: str = "unity",
    version: str | None = None,
    docset: str | None = None,
    limit: int = 10,
    member_type: str | None = None,
) -> str:
    """Search API/reference documentation within a selected engine/version/docset.

    Use this for symbol-style queries such as:
      - Unity: Transform.Rotate, Rigidbody, Quaternion.LookRotation
      - Unreal C++: UCableComponent, UCableComponent::SetAttachEndTo, FTransform
      - Unreal Blueprint: Cast To Actor, Get Actor Location

    Examples:
      - engine='unity'
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
    engine: str = "unity",
    version: str | None = None,
    docset: str | None = None,
    limit: int = 10,
    guide_type: str | None = None,
) -> str:
    """Search conceptual/guide documentation within a selected engine/version/docset.

    Examples:
      - engine='unity' for Manual pages
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
def get_engine_symbol_reference(
    symbol: str,
    engine: str = "unity",
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Resolve a single API symbol or Blueprint node to its structured reference."""

    try:
        ref = get_symbol_reference(symbol, engine=engine, version=version, docset=docset)
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
    engine: str = "unity",
    version: str | None = None,
    docset: str | None = None,
) -> str:
    """Retrieve a specific documentation page by relative path or substring."""

    try:
        payload = get_doc_page(path_or_key, engine=engine, version=version, docset=docset)
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
    engine: str = "unity",
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
    for key, value in sorted(stats["api_member_breakdown"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"  - {key or '(unknown)'}: {value}")
    lines += ["", "Guide-type breakdown:"]
    for key, value in sorted(stats["guide_breakdown"].items(), key=lambda item: (-item[1], item[0])):
        lines.append(f"  - {key or '(unknown)'}: {value}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Backwards-compatible Unity wrappers
# ---------------------------------------------------------------------------


@mcp.tool()
def search_unity_api(query: str, limit: int = 10, member_type: str | None = None) -> str:
    """Compatibility wrapper around search_api_reference(engine='unity')."""

    return search_api_reference(
        query=query,
        engine="unity",
        limit=limit,
        member_type=member_type,
    )


@mcp.tool()
def search_unity_guides(query: str, limit: int = 10, guide_type: str | None = None) -> str:
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
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    transport = "streamable-http"
    if "--stdio" in sys.argv:
        transport = "stdio"

    if transport == "streamable-http":
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
        print(f"Documentation MCP server starting on http://{host}:{port}/mcp", file=sys.stderr)
        mcp.settings.host = host
        mcp.settings.port = port

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
