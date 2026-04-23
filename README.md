# game-engine-mcp

An MCP server for offline game engine documentation with hybrid keyword + semantic search, cross-engine translation, and structural navigation.

Current built-in docsets:

- `godot:4.6:reference` -> Godot Engine class reference + manual docs from `docs/godot/4.6/`
- `unity:6000.4.3f1:reference` -> Unity Manual + ScriptReference from `docs/unity/6000.4.3f1/reference/`
- `unreal:4.26:cpp-api` -> Unreal Engine 4.26 C++ API from `docs/unreal/4.26/cpp-api/`
- `unreal:4.26:blueprint-api` -> Unreal Engine 4.26 Blueprint API from `docs/unreal/4.26/blueprint-api/`

## Architecture

The repo is organized around **docsets**. A docset is one engine/version/documentation-slice combination such as `unreal:4.26:cpp-api`.

Each docset has:

- A source directory on disk
- A parser kind
- Its own SQLite database under `data/<engine>/<version>/<docset>.db`
- Its own API and guide indexes inside that database
- An optional LanceDB vector store under `data/vectors/` for semantic search

That separation is intentional:

- Unreal C++ has roughly hundreds of thousands of pages and should not share a giant mixed index with Unity.
- Different engines can keep different parsing logic and metadata fields while still using one search/index/server pipeline.
- Future engines or versions are added by registering a new docset, not by cloning the whole server.

### Search pipeline

The search pipeline has three modes:

1. **Keyword (FTS5 + BM25)** -- fast, exact match. Best for precise symbol lookups like `Transform.Rotate`.
2. **Semantic (vector)** -- uses `all-MiniLM-L6-v2` embeddings stored in LanceDB. Best for natural language queries like "how to move a character".
3. **Hybrid (default)** -- merges both via Reciprocal Rank Fusion (RRF). Best for most queries.

Canonical source layout:

```text
docs/
  <engine>/
    <version>/
      <docset>/
```

Examples:

- `docs/godot/4.6/`
- `docs/unity/6000.4.3f1/reference/`
- `docs/unreal/4.26/cpp-api/`
- `docs/unreal/4.26/blueprint-api/`

The docset registry lives in [`docsets.json`](docsets.json). Adding a new engine/version/docset usually means:

1. Add a new entry to `docsets.json`
2. Reuse an existing parser kind or add a new parser
3. Build that docset's index
4. Optionally build the vector index for semantic search

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
      godot.py                 # Godot class reference + manual parser
      unity.py                 # Unity HTML parser
      unreal.py                # Unreal C++ / Blueprint HTML parsers
    embedding.py               # Sentence-transformers embedding model wrapper
    vecsearch.py               # LanceDB vector search + hybrid RRF fusion
    crossengine.py             # Cross-engine concept/symbol translation
    navigation.py              # Class hierarchy, member listing, module browsing
    indexer.py                 # Single-docset and multi-docset index builders
    search.py                  # Multi-docset keyword search and retrieval
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

This installs all dependencies including `sentence-transformers`, `lancedb`, and `numpy`.

## List Registered Docsets

```bash
uv run python scripts/build_index.py --list-docsets
```

## Build Indexes

Build keyword indexes for all configured docsets that exist on disk:

```bash
uv run python scripts/build_index.py
```

Build a specific engine docset:

```bash
uv run python scripts/build_index.py --engine godot --version 4.6 --docset reference
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

Build keyword + vector indexes together:

```bash
uv run python scripts/build_index.py --vectors -v
```

Or build the vector index separately after the keyword index exists:

```bash
make vecindex
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
    "gameEngineMCP": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

You can change the server key from `gameEngineMCP` to any name your client prefers.

### Local stdio setup

If you want the MCP client to launch this repo directly over stdio:

```json
{
  "mcpServers": {
    "gameEngineMCP": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/game-engine-mcp",
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
    "gameEngineMCP": {
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

### Search tools

| Tool | Description |
|------|-------------|
| `search_engine_docs` | Hybrid keyword + semantic search. Supports `mode="keyword"`, `"semantic"`, or `"hybrid"`. |
| `search_api_reference` | Pure keyword (FTS5) search for API symbols. |
| `search_engine_guides` | Pure keyword (FTS5) search for guides/manuals. |
| `answer_engine_question` | Combined API + guide keyword search. |

### Retrieval tools

| Tool | Description |
|------|-------------|
| `get_engine_symbol_reference` | Resolve a single API symbol to its full reference. |
| `get_engine_doc_page` | Retrieve a doc page by path. |
| `get_index_stats` | Statistics about the selected indexes. |
| `list_documentation_targets` | List registered docsets and their status. |

### Navigation tools

| Tool | Description |
|------|-------------|
| `browse_class_hierarchy` | Browse a class with all methods, properties, signals, and inheritance. |
| `list_class_members` | List members of a class, optionally filtered by type. |
| `browse_inheritance_chain` | Show the full parent chain for a class. |
| `list_engine_classes` | List all classes in an engine, with optional prefix filter. |
| `browse_module` | Browse a module or namespace with its classes and stats. |
| `get_related_symbols` | Find symbols related to a given one (same class, same topic). |

### Cross-engine tools

| Tool | Description |
|------|-------------|
| `translate_symbol` | Find the equivalent of a symbol in a different engine (e.g. Unity Rigidbody -> Godot RigidBody3D). |
| `compare_across_engines` | Look up a symbol across all engines and show equivalents side by side. |

### Index management

| Tool | Description |
|------|-------------|
| `build_vector_index` | Build or rebuild the LanceDB vector index from the existing SQLite data. |

All tools (except cross-engine ones) accept `engine`, `version`, and optional `docset` filters.

### Example tool calls

- Godot:
  `search_api_reference(query="Node.add_child", engine="godot", version="4.6")`
- Unity:
  `search_api_reference(query="Transform.Rotate", engine="unity")`
- Unreal C++:
  `search_api_reference(query="UCableComponent::SetAttachEndTo", engine="unreal", version="4.26", docset="cpp-api")`
- Unreal Blueprint:
  `get_engine_symbol_reference(symbol="Cast To Actor", engine="unreal", version="4.26", docset="blueprint-api")`
- Godot guides:
  `search_engine_guides(query="Introduction to Godot", engine="godot", version="4.6")`
- Hybrid semantic search:
  `search_engine_docs(query="how to move a character", engine="godot", mode="hybrid")`
- Cross-engine translation:
  `translate_symbol(symbol="Rigidbody", source_engine="unity", target_engine="godot")`
- Browse class:
  `browse_class_hierarchy(class_name="Transform", engine="unity")`
- List methods:
  `list_class_members(class_name="Node", engine="godot", member_type="method")`
- Compare across engines:
  `compare_across_engines(symbol="Camera")`

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

Godot parser extracts:

- Class and scope pages from `classes/class_*.html`
- Member-level anchors for signals, properties, theme properties, constructors, methods, operators, constants, annotations, enums, and enum constants
- Guide/manual pages from the rest of the Sphinx docs tree
- Title, class name, member type, signature, parameters, summary, remarks, topic path, and inheritance when present

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
- The checked-in `docs/godot/4.6/` dump is currently branded in-page as Godot `latest` / dev docs, so strict 4.6 accuracy depends on replacing that snapshot with a true 4.6 export.
- Vector search uses `fastembed` with the `BAAI/bge-small-en-v1.5` ONNX model (~130MB, auto-downloaded on first use). No PyTorch or GPU required. Falls back gracefully to keyword-only results if the model is unavailable.
- The vector index is stored separately from SQLite in `data/vectors/` and can be rebuilt independently.

## Verification

Current automated coverage:

```bash
uv run python -m pytest tests/ -v
```

45 tests covering search, navigation, cross-engine translation, vector search, and parsers.
