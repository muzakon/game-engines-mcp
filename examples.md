# Examples

This file shows how to connect the MCP server and how to prompt clients like Claude Code, Claude Desktop, Cursor, or other MCP-aware tools.

## Important

You do not need special prompt syntax.

Once the MCP server is connected, you can use normal language. The most useful things to mention are:

- engine
- version
- docset, if needed
- whether you want search results, an exact symbol reference, a page lookup, or a summary

## MCP Client Config Examples

### HTTP / URL setup

If the server is already running on the default port:

```json
{
  "mcpServers": {
    "gameEngineMCP": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

### Local stdio setup

If you want the MCP client to launch this repo directly:

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

### Published package template

If you later publish this project as a package, the config can look like this:

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

## Prompt Examples

### Hybrid / semantic search (new)

These use `search_engine_docs` which combines keyword + vector search:

- `Search the docs for "how to implement double jump" in Godot.`
- `Use the docs MCP and find pages about particle effects in Unity.`
- `Find documentation about spawning enemies in Unreal, use hybrid search.`
- `Search engine docs for "camera follow player" in Godot 4.6.`
- `Use semantic search to find Godot docs about saving and loading game state.`

### Unity examples

- `Use the docs MCP server to find the Unity documentation for Transform.Rotate and summarize the signature and parameters.`
- `Use Unity 6000.4.3f1 reference docs and explain Rigidbody.velocity.`
- `Search Unity docs for how to rotate a GameObject and summarize the best approach.`
- `Find the exact Unity doc page for Quaternion.LookRotation and explain when to use it.`

### Unreal Engine 4.26 C++ examples

- `Use Unreal Engine 4.26 C++ API docs and find UCableComponent::SetAttachEndTo.`
- `Look up Unreal 4.26 cpp-api docs for FTransform and summarize the important parts.`
- `Find the Unreal 4.26 C++ documentation for UWorld::SpawnActor and explain the parameters.`
- `Use the local documentation server, engine=unreal, version=4.26, docset=cpp-api, and find FString.`

### Unreal Engine 4.26 Blueprint examples

- `Use Unreal 4.26 Blueprint API docs and explain the Cast To Actor node.`
- `Search the Unreal 4.26 blueprint-api docset for Get Actor Location and list the inputs and outputs.`
- `Find the Blueprint node Cast To MovieSceneActorReferenceSection and explain its pins.`

### Navigation examples (new)

- `Browse the Transform class in Unity docs and show all its methods and properties.`
- `Show me the full inheritance chain for CharacterBody3D in Godot 4.6.`
- `List all methods of the Node class in Godot.`
- `Show me all classes starting with "Rigid" in Godot 4.6.`
- `What members does UCableComponent have? Filter to methods only.`
- `Find symbols related to Transform.position in Unity docs.`
- `Browse the Physics module in Unity docs.`

### Cross-engine translation examples (new)

- `What is the Godot equivalent of Unity's Rigidbody?`
- `Translate Transform from Unity to Godot.`
- `Find the Unreal equivalent of Godot's Node.add_child.`
- `Compare Camera across Unity, Godot, and Unreal using the docs MCP.`
- `What is the Unity equivalent of Unreal's AActor?`
- `Compare how input handling works across all engines.`

### Comparison examples

- `Compare Unity Transform.Rotate and Unreal FRotator usage using the connected documentation MCP.`
- `Using the docs MCP server, compare Unity Rigidbody movement with Unreal CharacterMovementComponent at a high level.`
- `Compare the Godot and Unity approaches to scene management using the docs MCP.`

### If you want to force tool usage

If the client does not use the MCP tools reliably, add one short instruction like:

- `Use the connected MCP documentation server for this.`
- `Do not answer from memory; use the docs MCP server.`
- `Use the local docs MCP and cite the exact symbol or page you used.`

## Good Prompting Patterns

### Exact API lookup

Give the exact symbol or node name:

- `Transform.Rotate`
- `UCableComponent::SetAttachEndTo`
- `Cast To Actor`

### Conceptual / semantic lookup

Use natural language and mention the engine:

- `Search for "how to make a character jump" in Godot docs`
- `Find pages about physics simulation in Unity`
- `How does collision detection work in Unreal?`

### Navigation / exploration

Ask about structure:

- `Show me all members of the Node class in Godot`
- `What does the inheritance chain for Rigidbody look like in Unity?`
- `List all classes in the Unreal cpp-api docset`

### Cross-engine

Mention both engines:

- `What is the Godot equivalent of Unity's Rigidbody?`
- `Compare Camera across all engines`

### Ambiguous request

Mention the docset directly:

- `Use Unreal 4.26 cpp-api docs for FTransform`
- `Use Unreal 4.26 blueprint-api docs for Add Movement Input`

## Rule of Thumb

- Exact symbol question: give the exact symbol name.
- Conceptual question: mention engine, version, and topic.
- Natural language question: use `search_engine_docs` with `mode="hybrid"` or `"semantic"`.
- Unreal question: specify `cpp-api` or `blueprint-api` when needed.
- Cross-engine question: mention both source and target engine.
- If the client is not using MCP, explicitly say `use the docs MCP server`.
