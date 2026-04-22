"""MCP server exposing Unity documentation tools.

Supports both stdio and streamable HTTP transports.

The tool surface mirrors the two-index architecture:

- search_unity_api          -> precise API/symbol lookup
- search_unity_guides       -> conceptual / how-to lookup
- get_unity_symbol_reference-> structured single-symbol detail (API only)
- get_unity_doc_page        -> retrieve a specific page (either index)
- answer_unity_question     -> hybrid: search both indexes, label results
- get_unity_index_stats     -> index health
"""

from __future__ import annotations

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from .search import (
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
    format_search_results,
    format_symbol_ref,
)

logger = logging.getLogger(__name__)

mcp = FastMCP("unity-mcp")


@mcp.tool()
def search_unity_api(
    query: str,
    limit: int = 10,
    member_type: str | None = None,
) -> str:
    """Precise search across Unity's ScriptReference (classes, structs, enums,
    interfaces, methods, properties, fields, events). Use this for symbol-style
    queries like 'Transform.Rotate', 'Rigidbody', 'OnCollisionEnter',
    'Quaternion.LookRotation'. Ranking is weighted toward symbol/title/class
    matches, so exact identifiers surface first.

    Args:
        query: Symbol or API term, e.g. 'Transform.Rotate' or 'Rigidbody velocity'.
        limit: Max results (default 10, max 50).
        member_type: Optional filter: class | struct | enum | interface | method | property | field | event.
    """
    results = search_api(query, limit=limit, member_type=member_type)
    return format_search_results(results, header=f"API search: '{query}'")


@mcp.tool()
def search_unity_guides(
    query: str,
    limit: int = 10,
    guide_type: str | None = None,
) -> str:
    """Conceptual / how-to search across Unity's Manual (tutorials, overviews,
    workflows, editor usage, best practices). Use this for natural-language
    questions like 'how to rotate a cube', 'how to move with physics',
    'how to load a scene'. Ranking favors title and section-heading matches.

    Args:
        query: Natural-language question or topic.
        limit: Max results (default 10, max 50).
        guide_type: Optional filter: manual | tutorial | overview | reference | general.
    """
    results = search_guides(query, limit=limit, guide_type=guide_type)
    return format_search_results(results, header=f"Guide search: '{query}'")


@mcp.tool()
def get_unity_symbol_reference(symbol: str) -> str:
    """Look up a single Unity API symbol (class, method, property, enum, ...) by name.
    Returns the structured reference: signature, summary, parameters, returns,
    remarks, and a content excerpt. Examples: 'Transform', 'Transform.Rotate',
    'Rigidbody', 'Vector3', 'MonoBehaviour.Start'.

    Args:
        symbol: Symbol to resolve, e.g. 'Transform.Rotate' or 'Rigidbody'.
    """
    ref = get_symbol_reference(symbol)
    if ref:
        return format_symbol_ref(ref)
    return (
        f"No documentation found for symbol '{symbol}'. "
        "Try search_unity_api for related identifiers, or search_unity_guides "
        "for conceptual material."
    )


@mcp.tool()
def get_unity_doc_page(path_or_key: str) -> str:
    """Retrieve a specific Unity documentation page by relative path or substring.
    Tries the API index first, then the guide index. Returns the appropriate
    structured view (symbol reference for API, guide page for Manual).

    Args:
        path_or_key: Relative path of the doc page, e.g. 'en/ScriptReference/Transform.html'
            or 'en/Manual/class-Transform.html'. Substrings are accepted.
    """
    payload = get_doc_page(path_or_key)
    if payload:
        return format_doc_page(payload)
    return (
        f"No documentation page found matching '{path_or_key}'. "
        "Try search_unity_api or search_unity_guides to find the correct path."
    )


@mcp.tool()
def answer_unity_question(query: str, limit_per_index: int = 5) -> str:
    """Hybrid search: runs the question against BOTH the API index and the guide
    index and returns labeled results from each. Useful when you don't know
    whether a question is symbol-precise or conceptual. Each result is tagged
    with its source so you can cite whether the answer came from API or Guide docs.

    Args:
        query: Free-form Unity question.
        limit_per_index: Max results per index (default 5, max 50).
    """
    bundle = answer_question(query, limit_per_index=limit_per_index)
    return format_combined_results(bundle)


@mcp.tool()
def get_unity_index_stats() -> str:
    """Statistics about the indexed Unity documentation: per-index counts, unique
    classes/namespaces, member-type breakdown, guide-type breakdown.
    """
    s = get_stats()
    lines = [
        "Unity Documentation Index Statistics",
        "=" * 40,
        f"Total indexed pages: {s['total_pages']}",
        f"  - API pages:   {s['api_pages']}",
        f"  - Guide pages: {s['guide_pages']}",
        f"Unique classes:    {s['unique_classes']}",
        f"Unique namespaces: {s['unique_namespaces']}",
        "",
        "API member-type breakdown:",
    ]
    for k, v in sorted(s["api_member_breakdown"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  - {k or '(unknown)'}: {v}")
    lines.append("")
    lines.append("Guide-type breakdown:")
    for k, v in sorted(s["guide_breakdown"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  - {k or '(unknown)'}: {v}")
    return "\n".join(lines)


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
        host = os.environ.get("UNITY_MCP_HOST", "0.0.0.0")
        port = int(os.environ.get("UNITY_MCP_PORT", "8080"))
        for arg in sys.argv:
            if arg.startswith("--host="):
                host = arg.split("=", 1)[1]
            elif arg.startswith("--port="):
                port = int(arg.split("=", 1)[1])
        print(f"Unity MCP server starting on http://{host}:{port}/mcp", file=sys.stderr)
        mcp.settings.host = host
        mcp.settings.port = port

    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
