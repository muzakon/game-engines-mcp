# unity-mcp

A local MCP (Model Context Protocol) server that indexes offline Unity documentation into SQLite with FTS5 full-text search, then exposes MCP tools so Claude, Codex, and other MCP clients can query Unity documentation accurately without hallucinating APIs.

## How It Works

1. **Build step**: Recursively scans `Documentation/` for HTML files, parses structured data from each page (title, symbol, class, namespace, signature, parameters, summary, etc.), and stores everything in a local SQLite database with an FTS5 virtual table for fast text search.
2. **Server step**: Runs a stdio-based MCP server that exposes tools for searching docs, retrieving pages, and looking up symbols by name.

## Project Structure

```
unity-mcp/
  Documentation/          # Offline Unity HTML docs (source of truth)
  src/unity_mcp/
    __init__.py           # Package init
    config.py             # Paths and constants
    models.py             # Data models (DocRecord, SearchResult, SymbolReference)
    db.py                 # SQLite schema, connection management, upsert
    parser.py             # HTML parser for Unity doc pages
    indexer.py            # Orchestrates scanning + parsing + storing
    search.py             # Full-text search and symbol lookup logic
    server.py             # MCP server with tool definitions
    utils.py              # Formatting helpers
  scripts/
    build_index.py        # Build/rebuild the SQLite index
    run_server.py         # Run the MCP server
  data/
    unity_docs.db         # SQLite database (generated)
  tests/
    test_parser.py        # Parser tests
    test_search.py        # Search tests
  pyproject.toml
```

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```bash
cd unity-mcp
uv sync
```

## Build the Index

```bash
uv run python scripts/build_index.py
```

With verbose output:

```bash
uv run python scripts/build_index.py -v
```

Incremental update (no rebuild):

```bash
uv run python scripts/build_index.py --no-rebuild
```

## Run the MCP Server

```bash
uv run python scripts/run_server.py
```

The server communicates over stdio using the MCP protocol.

## Connect to an MCP Client

Add this to your MCP client configuration (e.g., Claude Desktop, Cursor, etc.):

```json
{
  "mcpServers": {
    "unity-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/unity-mcp",
        "run",
        "python",
        "scripts/run_server.py"
      ]
    }
  }
}
```

Or if you've installed the package:

```json
{
  "mcpServers": {
    "unity-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/unity-mcp",
        "run",
        "unity-mcp"
      ]
    }
  }
}
```

## Available Tools

### `search_unity_docs`

Full-text search over indexed Unity documentation.

```
Input:
  query (string, required) - Search query
  limit (int, optional) - Max results, default 10

Returns: Top matching pages with title, path, snippet, and relevance score.
```

Example: Search for "transform rotate" to find Transform.Rotate and related pages.

### `get_unity_doc_page`

Retrieve a specific documentation page by path.

```
Input:
  path_or_key (string, required) - Relative path like "en/ScriptReference/Transform.html"

Returns: Structured fields (title, summary, signature, parameters, content excerpt).
```

### `get_unity_symbol_reference`

Look up a Unity symbol (class, method, property, enum) by name.

```
Input:
  symbol (string, required) - Symbol name like "Transform.Rotate" or "Rigidbody"

Returns: Best match with signature, summary, parameters, returns, and remarks.
         If no match found, returns a clear "not found" message.
```

### `get_unity_index_stats`

Get statistics about the indexed documentation.

```
Returns: Total pages, script reference count, manual count, unique classes.
```

## Example Tool Usage

**Search**: "How do I rotate a transform?"
```
search_unity_docs(query="Transform rotate")
```

**Symbol lookup**: "What is Rigidbody?"
```
get_unity_symbol_reference(symbol="Rigidbody")
```

**Exact page**: "Show me the Transform.Rotate docs"
```
get_unity_doc_page(path_or_key="en/ScriptReference/Transform.Rotate.html")
```

## Architecture

- **Parser** (`parser.py`): Uses BeautifulSoup4 + lxml to extract structured data from Unity HTML docs. Handles both Script Reference pages (API docs with signatures, parameters) and Manual pages (conceptual guides). Degrades gracefully on non-standard pages.
- **Database** (`db.py`): SQLite with FTS5 virtual table synced via triggers. WAL mode for concurrent reads during indexing. Upsert-by-path to avoid duplicates.
- **Search** (`search.py`): Two-tier search — exact symbol/title/class match (boosted), then FTS5 BM25 ranking. Symbol lookup tries multiple strategies (exact name -> title -> suffix match -> class -> FTS).
- **Server** (`server.py`): Official Python MCP SDK, stdio transport. Four tools with structured responses.

## Limitations

- Only indexes HTML files; PDFs or other formats are not supported
- Symbol extraction relies on HTML patterns and may miss some edge cases
- No semantic/vector search — purely text-based FTS5
- The database must be rebuilt when documentation is updated
- Signatures are extracted as-is from the HTML; complex generic signatures may not parse perfectly

## Future Improvements

- Incremental indexing (only re-parse changed files)
- Semantic search via local embeddings
- Better namespace extraction
- Enum value indexing
- Type hierarchy tracking (inheritance chains)
- Cross-reference linking between Script Reference and Manual
