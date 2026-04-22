"""MCP server exposing Unity documentation tools over stdio.

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
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

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

app = Server("unity-mcp")


_TOOLS: list[Tool] = [
    Tool(
        name="search_unity_api",
        description=(
            "Precise search across Unity's ScriptReference (classes, structs, enums, "
            "interfaces, methods, properties, fields, events). Use this for symbol-style "
            "queries like 'Transform.Rotate', 'Rigidbody', 'OnCollisionEnter', "
            "'Quaternion.LookRotation'. Ranking is weighted toward symbol/title/class "
            "matches, so exact identifiers surface first."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Symbol or API term, e.g. 'Transform.Rotate' or 'Rigidbody velocity'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 50).",
                    "default": 10,
                },
                "member_type": {
                    "type": "string",
                    "description": (
                        "Optional filter: class | struct | enum | interface | method | "
                        "property | field | event."
                    ),
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="search_unity_guides",
        description=(
            "Conceptual / how-to search across Unity's Manual (tutorials, overviews, "
            "workflows, editor usage, best practices). Use this for natural-language "
            "questions like 'how to rotate a cube', 'how to move with physics', "
            "'how to load a scene'. Ranking favors title and section-heading matches."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language question or topic.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max results (default 10, max 50).",
                    "default": 10,
                },
                "guide_type": {
                    "type": "string",
                    "description": "Optional filter: manual | tutorial | overview | reference | general.",
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_unity_symbol_reference",
        description=(
            "Look up a single Unity API symbol (class, method, property, enum, ...) by name. "
            "Returns the structured reference: signature, summary, parameters, returns, "
            "remarks, and a content excerpt. Examples: 'Transform', 'Transform.Rotate', "
            "'Rigidbody', 'Vector3', 'MonoBehaviour.Start'."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Symbol to resolve, e.g. 'Transform.Rotate' or 'Rigidbody'.",
                },
            },
            "required": ["symbol"],
        },
    ),
    Tool(
        name="get_unity_doc_page",
        description=(
            "Retrieve a specific Unity documentation page by relative path or substring. "
            "Tries the API index first, then the guide index. Returns the appropriate "
            "structured view (symbol reference for API, guide page for Manual)."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "path_or_key": {
                    "type": "string",
                    "description": (
                        "Relative path of the doc page, e.g. 'en/ScriptReference/Transform.html' "
                        "or 'en/Manual/class-Transform.html'. Substrings are accepted."
                    ),
                },
            },
            "required": ["path_or_key"],
        },
    ),
    Tool(
        name="answer_unity_question",
        description=(
            "Hybrid search: runs the question against BOTH the API index and the guide "
            "index and returns labeled results from each. Useful when you don't know "
            "whether a question is symbol-precise or conceptual. Each result is tagged "
            "with its source so you can cite whether the answer came from API or Guide docs."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Free-form Unity question.",
                },
                "limit_per_index": {
                    "type": "integer",
                    "description": "Max results per index (default 5, max 50).",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="get_unity_index_stats",
        description=(
            "Statistics about the indexed Unity documentation: per-index counts, unique "
            "classes/namespaces, member-type breakdown, guide-type breakdown."
        ),
        inputSchema={"type": "object", "properties": {}},
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    return _TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    logger.debug("Tool called: %s with args: %s", name, arguments)

    if name == "search_unity_api":
        query = (arguments.get("query") or "").strip()
        if not query:
            return [TextContent(type="text", text="Please provide a search query.")]
        results = search_api(
            query,
            limit=int(arguments.get("limit", 10)),
            member_type=(arguments.get("member_type") or None),
        )
        return [TextContent(type="text", text=format_search_results(
            results, header=f"API search: '{query}'"
        ))]

    if name == "search_unity_guides":
        query = (arguments.get("query") or "").strip()
        if not query:
            return [TextContent(type="text", text="Please provide a search query.")]
        results = search_guides(
            query,
            limit=int(arguments.get("limit", 10)),
            guide_type=(arguments.get("guide_type") or None),
        )
        return [TextContent(type="text", text=format_search_results(
            results, header=f"Guide search: '{query}'"
        ))]

    if name == "get_unity_symbol_reference":
        symbol = (arguments.get("symbol") or "").strip()
        if not symbol:
            return [TextContent(type="text", text="Please provide a symbol name.")]
        ref = get_symbol_reference(symbol)
        if ref:
            return [TextContent(type="text", text=format_symbol_ref(ref))]
        return [TextContent(
            type="text",
            text=(
                f"No documentation found for symbol '{symbol}'. "
                "Try search_unity_api for related identifiers, or search_unity_guides "
                "for conceptual material."
            ),
        )]

    if name == "get_unity_doc_page":
        path_or_key = (arguments.get("path_or_key") or "").strip()
        if not path_or_key:
            return [TextContent(type="text", text="Please provide a path or key.")]
        payload = get_doc_page(path_or_key)
        if payload:
            return [TextContent(type="text", text=format_doc_page(payload))]
        return [TextContent(
            type="text",
            text=(
                f"No documentation page found matching '{path_or_key}'. "
                "Try search_unity_api or search_unity_guides to find the correct path."
            ),
        )]

    if name == "answer_unity_question":
        query = (arguments.get("query") or "").strip()
        if not query:
            return [TextContent(type="text", text="Please provide a question.")]
        bundle = answer_question(query, limit_per_index=int(arguments.get("limit_per_index", 5)))
        return [TextContent(type="text", text=format_combined_results(bundle))]

    if name == "get_unity_index_stats":
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
        return [TextContent(type="text", text="\n".join(lines))]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def run() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        stream=sys.stderr,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    import asyncio
    asyncio.run(run())


if __name__ == "__main__":
    main()
