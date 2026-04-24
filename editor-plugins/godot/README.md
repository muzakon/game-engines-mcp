# Game Engine MCP - Godot Plugin

A Godot 4 editor addon that opens a TCP command port for live editor interaction via the [game-engine-mcp](../../) Python server. Lets AI assistants read console errors, browse scene trees, manipulate nodes, control play mode, and more.

Written entirely in GDScript using Godot's built-in `TCPServer` class. No external dependencies.

## Requirements

- Godot 4.0 or newer
- No additional packages or plugins needed

## Installation

### Option A: Copy into project

1. Copy the `addons/game_engine_mcp/` folder into your Godot project:

```
YourGodotProject/
  addons/
    game_engine_mcp/       <-- copy this entire folder
      plugin.cfg
      plugin.gd
      mcp_server.gd
      console_capturer.gd
      commands/
        commands.gd
```

2. Open your project in the Godot Editor.

3. Go to **Project > Project Settings > Plugins** (or the **Addon** tab in Godot 4.6+).

4. Find **"Game Engine MCP"** in the list and enable it.

5. You should see `[GameEngineMCP] Plugin loaded` and `[GameEngineMCP] Listening on 127.0.0.1:9879` in the Output panel.

### Option B: Install from the Asset Library (future)

If published to the Godot Asset Library:

1. **AssetLib** tab in the editor.
2. Search for **"Game Engine MCP"**.
3. Download and enable.

## Setup

### 1. Configure the plugin

The addon starts automatically when enabled and listens on `127.0.0.1:9879`.

To change the port, edit the defaults in `mcp_server.gd` or call `start_server(host, port)` before the default auto-start.

### 2. Configure the Python MCP server

In your `engines.local.yaml` (at the game-engine-mcp project root):

```yaml
bridges:
  godot:
    host: "127.0.0.1"
    port: 9879
    auto_connect: true
```

### 3. Start the MCP server

```bash
cd /path/to/game-engine-mcp
uv run python scripts/run_server.py
```

The MCP server will auto-connect to Godot on startup (if `auto_connect: true`).

### 4. Connect from your AI client

Add to your MCP client configuration (e.g. `.cursor/mcp.json` or Claude Desktop config):

```json
{
  "mcpServers": {
    "gameEngineMCP": {
      "url": "http://localhost:8080/mcp"
    }
  }
}
```

## Available MCP Tools

Once connected, the following tools work with `engine='godot'`:

| Tool | Example |
|------|---------|
| `editor_connect` | `editor_connect(engine='godot')` |
| `editor_status` | `editor_status()` |
| `editor_get_console` | `editor_get_console(engine='godot', count=20, level='error')` |
| `editor_clear_console` | `editor_clear_console(engine='godot')` |
| `editor_get_scene_hierarchy` | `editor_get_scene_hierarchy(engine='godot')` |
| `editor_get_object` | `editor_get_object(engine='godot', path='Player')` |
| `editor_create_object` | `editor_create_object(engine='godot', name='Enemy', type='CharacterBody2D')` |
| `editor_delete_object` | `editor_delete_object(engine='godot', path='OldNode')` |
| `editor_set_property` | `editor_set_property(engine='godot', path='Player', component='', property='position', value=[10, 5])` |
| `editor_get_properties` | `editor_get_properties(engine='godot', path='Player')` |
| `editor_move_object` | `editor_move_object(engine='godot', path='Player', position=[10, 0, 5])` |
| `editor_play` | `editor_play(engine='godot')` |
| `editor_pause` | `editor_pause(engine='godot')` |
| `editor_stop` | `editor_stop(engine='godot')` |
| `editor_list_assets` | `editor_list_assets(engine='godot', path='res://scenes')` |
| `editor_save_scene` | `editor_save_scene(engine='godot')` |
| `editor_take_screenshot` | `editor_take_screenshot(engine='godot')` |
| `editor_execute_code` | `editor_execute_code(engine='godot', code='print("hello")')` |
| `editor_disconnect` | `editor_disconnect(engine='godot')` |

## Supported Node Types for Creation

The `create_object` tool supports these type shortcuts:

| Type | Godot Class |
|------|-------------|
| `Node2D` | `Node2D` |
| `Node3D` / `Spatial` | `Node3D` |
| `CharacterBody2D` | `CharacterBody2D` |
| `CharacterBody3D` | `CharacterBody3D` |
| `RigidBody2D` | `RigidBody2D` |
| `RigidBody3D` | `RigidBody3D` |
| `Camera2D` | `Camera2D` |
| `Camera3D` | `Camera3D` |
| `Sprite2D` | `Sprite2D` |
| `Sprite3D` | `Sprite3D` |
| `MeshInstance3D` / `Cube` | `MeshInstance3D` (with BoxMesh) |
| `CollisionShape2D` | `CollisionShape2D` |
| `CollisionShape3D` | `CollisionShape3D` |
| `Area2D` | `Area2D` |
| `Area3D` | `Area3D` |
| `Light2D` | `PointLight2D` |
| `Light3D` | `DirectionalLight3D` |
| Any Godot class name | `ClassDB.instantiate(type)` |

## Plugin File Structure

```
addons/
  game_engine_mcp/
    plugin.cfg                # Godot plugin manifest
    plugin.gd                 # EditorPlugin entry point (preloads McpServer)
    mcp_server.gd             # TCP server + all command implementations
    console_capturer.gd       # Console log ring buffer
```

## Differences from Unity Plugin

| Aspect | Unity Plugin | Godot Plugin |
|--------|-------------|--------------|
| Language | C# | GDScript |
| JSON library | Newtonsoft.Json | Built-in `JSON` class |
| TCP server | `System.Net.Sockets.TcpListener` | Built-in `TCPServer` |
| Console capture | `Application.logMessageReceived` | `OS.print_error` / `OS.print_warning` signals |
| Property access | `SerializedObject` + reflection | `get_property_list()` + `set()` |
| Code execution | Limited C# eval | `Expression` class (full GDScript eval) |
| Screenshots | `RenderTexture` + `Camera.Render` | `Viewport.get_texture().get_image()` |

## Troubleshooting

### Plugin does not appear in Project Settings > Plugins

- Ensure `plugin.cfg` is at `addons/game_engine_mcp/plugin.cfg` (exact path matters).
- Restart the editor after copying files.

### "Failed to listen" error

- Port 9879 may be in use. Only one instance can bind to a port at a time.
- Close other Godot editors or change the port in `mcp_server.gd`.

### MCP server cannot connect

- Check the Output panel in Godot for `[GameEngineMCP] Listening on ...`.
- Verify the port matches between the plugin and `engines.local.yaml`.
- If connecting from a different machine, change the host binding.

### Console capture shows limited output

- Godot's console capture hooks (`OS.print_error`, `OS.print_warning`) only catch error and warning output. Regular `print()` output is not capturable through Godot's API in editor plugins. Use `push_error()` or `push_warning()` in your scripts for log output you want the MCP server to see.

## Security

The TCP server binds to `127.0.0.1` (localhost only) by default. Only change this if you understand the implications.
