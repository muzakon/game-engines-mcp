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
    "unityMCP": {
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

### Published package template

If you later publish this project as a package, the config can look like this:

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

## Prompt Examples

### Unity examples

- `Use the docs MCP server to find the Unity documentation for Transform.Rotate and summarize the signature and parameters.`
- `Use Unity current reference docs and explain Rigidbody.velocity.`
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

### Comparison examples

- `Compare Unity Transform.Rotate and Unreal FRotator usage using the connected documentation MCP.`
- `Using the docs MCP server, compare Unity Rigidbody movement with Unreal CharacterMovementComponent at a high level.`

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

### Conceptual lookup

Say the engine and version clearly:

- `Use Unity current docs`
- `Use Unreal 4.26 cpp-api docs`
- `Use Unreal 4.26 blueprint-api docs`

### Ambiguous request

Mention the docset directly:

- `Use Unreal 4.26 cpp-api docs for FTransform`
- `Use Unreal 4.26 blueprint-api docs for Add Movement Input`

## Rule of Thumb

- Exact symbol question: give the exact symbol name.
- Conceptual question: mention engine, version, and topic.
- Unreal question: specify `cpp-api` or `blueprint-api` when needed.
- If the client is not using MCP, explicitly say `use the docs MCP server`.
