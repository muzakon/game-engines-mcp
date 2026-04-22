# game-engine-mcp

An MCP server for offline game engine documentation. The codebase now supports multiple engines, multiple versions, and multiple docsets without collapsing everything into one database.

Current built-in docsets:

- `unity:current:reference` -> Unity Manual + ScriptReference from `docs/unity/current/reference/`
- `unreal:4.26:cpp-api` -> Unreal Engine 4.26 C++ API from `docs/unreal/4.26/cpp-api/`
- `unreal:4.26:blueprint-api` -> Unreal Engine 4.26 Blueprint API from `docs/unreal/4.26/blueprint-api/`

## Architecture

The repo is organized around **docsets**. A docset is one engine/version/documentation-slice combination such as `unreal:4.26:cpp-api`.

Each docset has:

- A source directory on disk
- A parser kind
- Its own SQLite database under `data/<engine>/<version>/<docset>.db`
- Its own API and guide indexes inside that database

That separation is intentional:

- Unreal C++ has roughly hundreds of thousands of pages and should not share a giant mixed index with Unity.
- Different engines can keep different parsing logic and metadata fields while still using one search/index/server pipeline.
- Future engines or versions are added by registering a new docset, not by cloning the whole server.

Canonical source layout:

```text
docs/
  <engine>/
    <version>/
      <docset>/
```

Examples:

- `docs/unity/current/reference/`
- `docs/unreal/4.26/cpp-api/`
- `docs/unreal/4.26/blueprint-api/`

The docset registry lives in [`docsets.json`](docsets.json). Adding a new engine/version/docset usually means:

1. Add a new entry to `docsets.json`
2. Reuse an existing parser kind or add a new parser
3. Build that docset’s index

## Project Structure

```text
game-engine-mcp/
  docsets.json                 # Registry of engine/version/docset targets
  docs/                        # All offline docs in engine/version/docset layout
  src/
    config.py                  # Global constants and defaults
    docsets.py                 # Docset manifest loading and selection
    models.py                  # Shared record/result/reference models
    db.py                      # Common SQLite schema for per-docset databases
    parser.py                  # Parser dispatch + file discovery
    parsers/
      unity.py                 # Unity HTML parser
      unreal.py                # Unreal C++ / Blueprint HTML parsers
    indexer.py                 # Single-docset and multi-docset index builders
    search.py                  # Multi-docset search and retrieval
    server.py                  # MCP tools and compatibility wrappers
    utils.py                   # Formatting helpers
  scripts/
    build_index.py             # Build indexes for selected docsets
    run_server.py              # Start the MCP server
  tests/
```

## Installation

Requires Python 3.11+ and `uv`.

```bash
uv sync
```

## List Registered Docsets

```bash
uv run python scripts/build_index.py --list-docsets
```

## Build Indexes

Build the default Unity index:

```bash
uv run python scripts/build_index.py
```

Build a specific Unreal docset:

```bash
uv run python scripts/build_index.py --engine unreal --version 4.26 --docset cpp-api
uv run python scripts/build_index.py --engine unreal --version 4.26 --docset blueprint-api
```

Build all registered docsets that exist on disk:

```bash
uv run python scripts/build_index.py --all
```

Incremental rebuild:

```bash
uv run python scripts/build_index.py --engine unreal --version 4.26 --docset cpp-api --no-rebuild
```

## Run the MCP Server

HTTP transport:

```bash
uv run python scripts/run_server.py
```

Stdio transport:

```bash
uv run python scripts/run_server.py --stdio
```

Environment variables:

- `GAME_DOCS_MCP_HOST`
- `GAME_DOCS_MCP_PORT`

Legacy Unity env vars still work:

- `UNITY_MCP_HOST`
- `UNITY_MCP_PORT`

## MCP Client Setup

After building the indexes and starting the server, add it to your MCP client.

### HTTP / URL setup

If you run the server over HTTP on the default port:

```json
{
  "mcpServers": {
    "unityMCP": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

You can change the server key from `unityMCP` to any name your client prefers.

### Local stdio setup

If you want the MCP client to launch this repo directly over stdio:

```json
{
  "mcpServers": {
    "unityMCP": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/unity-mcp",
        "run",
        "python",
        "scripts/run_server.py",
        "--stdio"
      ]
    }
  }
}
```

### Published package setup

If you later publish this project as a package, the stdio configuration can use `uvx` instead of a local repo path. Example template:

```json
{
  "mcpServers": {
    "unityMCP": {
      "command": "uvx",
      "args": [
        "--from",
        "<your-package-name>",
        "<your-entry-command>",
        "--stdio"
      ]
    }
  }
}
```

Use the real published package name and command when you have one.

## MCP Tools

Primary tools:

- `list_documentation_targets`
- `search_api_reference`
- `search_engine_guides`
- `get_engine_symbol_reference`
- `get_engine_doc_page`
- `answer_engine_question`
- `get_index_stats`

The generic tools take `engine`, `version`, and optional `docset`.

Examples:

- Unity:
  `search_api_reference(query="Transform.Rotate", engine="unity")`
- Unreal C++:
  `search_api_reference(query="UCableComponent::SetAttachEndTo", engine="unreal", version="4.26", docset="cpp-api")`
- Unreal Blueprint:
  `get_engine_symbol_reference(symbol="Cast To Actor", engine="unreal", version="4.26", docset="blueprint-api")`

Backwards-compatible Unity wrappers still exist:

- `search_unity_api`
- `search_unity_guides`
- `get_unity_symbol_reference`
- `get_unity_doc_page`
- `answer_unity_question`
- `get_unity_index_stats`

## Parser Coverage

Unity parser extracts:

- ScriptReference symbols
- Manual/guide pages
- Title, symbol/class, namespace, member type, signature, parameters, returns, remarks, summary

Unreal C++ parser extracts:

- Class/module/member pages
- QuickStart/guide pages
- Module, header, include, source, hierarchy, signature, parameters, summary, remarks

Unreal Blueprint parser extracts:

- Node title
- Node type/signature
- Inputs and outputs
- Topic path/category

## Notes

- Searches are isolated to the selected docset databases, then merged at query time when you intentionally search across multiple docsets.
- The common schema is shared, but parsers are engine-specific.
- Not every field is populated for every engine; empty fields are expected where a doc format does not provide that concept.

## Verification

Current automated coverage:

```bash
.venv/bin/pytest -q
```

At the time of the latest local run, all tests passed.
