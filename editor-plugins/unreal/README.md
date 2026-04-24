# Game Engine MCP - Unreal Engine Plugin

A Python-based TCP command server that runs inside the Unreal Editor for live editor interaction via the [game-engine-mcp](../../) Python MCP server. Lets AI assistants read console errors, manipulate levels, edit actor properties, control play mode, and more.

Written in pure Python using Unreal Engine's built-in `unreal` module and Python's `socketserver`. No C++ plugin compilation required.

## Requirements

- Unreal Engine 5.0 or newer
- **Python Editor Script Plugin** enabled (Edit > Plugins > Scripting)
- **Editor Scripting Utilities** plugin enabled (recommended, for `EditorLevelLibrary` etc.)

## Installation

### Option A: Project Python folder (recommended)

1. Copy `unreal_server_init.py` and the `game_engine_mcp_unreal/` package to your project's `Content/Python/` folder:

```
YourUEProject/
  Content/
    Python/
      unreal_server_init.py
      game_engine_mcp_unreal/
        __init__.py
        ...
```

2. Create or edit `Content/Python/init_unreal.py` to auto-start the server:

```python
# Content/Python/init_unreal.py
import unreal_server_init
unreal_server_init.start_server()
```

3. Restart the Unreal Editor. The server starts automatically.

### Option B: Manual start

1. Copy `unreal_server_init.py` and the `game_engine_mcp_unreal/` package to any location on disk.
2. In the UE editor, open the Output Log and switch to Python mode (dropdown > Python).
3. Run:
```python
import sys
sys.path.insert(0, "path/to/unreal")
exec(open("path/to/unreal/unreal_server_init.py").read()); start_server()
```

### Option C: Startup scripts list

1. Go to **Edit > Project Settings > Plugins > Python**.
2. Add `unreal_server_init.py` to the **Startup Scripts** list.
3. Restart the editor.

## Setup

### 1. Configure the plugin

Edit `game_engine_mcp_unreal/config.py`:

```python
HOST = "127.0.0.1"
PORT = 9878
AUTO_START = True
```

### 2. Configure the Python MCP server

In your `engines.local.yaml` (at the game-engine-mcp project root):

```yaml
bridges:
  unreal:
    host: "127.0.0.1"
    port: 9878
    auto_connect: true
```

### 3. Start the MCP server

```bash
cd /path/to/game-engine-mcp
uv run python scripts/run_server.py
```

The MCP server will auto-connect to the Unreal plugin on startup (if `auto_connect: true`).

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

Once connected, the following tools work with `engine='unreal'`:

| Tool | Example |
|------|---------|
| `editor_connect` | `editor_connect(engine='unreal')` |
| `editor_status` | `editor_status()` |
| `editor_get_console` | `editor_get_console(engine='unreal', count=20, level='error')` |
| `editor_clear_console` | `editor_clear_console(engine='unreal')` |
| `editor_get_scene_hierarchy` | `editor_get_scene_hierarchy(engine='unreal')` |
| `editor_get_object` | `editor_get_object(engine='unreal', path='Player')` |
| `editor_create_object` | `editor_create_object(engine='unreal', name='Floor', type='Cube')` |
| `editor_delete_object` | `editor_delete_object(engine='unreal', path='OldActor')` |
| `editor_set_property` | `editor_set_property(engine='unreal', path='Player', component='', property='RelativeLocation', value=[0,5,0])` |
| `editor_get_properties` | `editor_get_properties(engine='unreal', path='Player')` |
| `editor_move_object` | `editor_move_object(engine='unreal', path='Player', position=[10,0,5])` |
| `editor_play` | `editor_play(engine='unreal')` |
| `editor_pause` | `editor_pause(engine='unreal')` |
| `editor_stop` | `editor_stop(engine='unreal')` |
| `editor_list_assets` | `editor_list_assets(engine='unreal', path='/Game/Characters')` |
| `editor_save_scene` | `editor_save_scene(engine='unreal')` |
| `editor_take_screenshot` | `editor_take_screenshot(engine='unreal')` |
| `editor_execute_code` | `editor_execute_code(engine='unreal', code='print("hello")', language='python')` |
| `editor_disconnect` | `editor_disconnect(engine='unreal')` |

The Unreal bridge also exposes UE-specific tools:

- Level: `editor_new_level`, `editor_open_level`, `editor_save_all_levels`
- Actor: `editor_find_actors`, `editor_duplicate_actor`, `editor_set_actor_visible`
- Asset: `editor_get_asset`, `editor_import_asset`, `editor_delete_asset`, `editor_move_asset`, `editor_rename_asset`
- Content: `editor_get_content_directory`, `editor_get_project_dir`
- Viewport: `editor_get_viewport_camera`, `editor_set_viewport_camera`
- Selection: `editor_get_selection`, `editor_set_selection`

## Supported Object Types for Creation

The `create_object` tool supports these type shortcuts:

| Type | UE Class |
|------|----------|
| `Empty` / `Actor` | `Actor` |
| `Cube` / `CubeMesh` | `StaticMeshActor` (with Cube mesh) |
| `Sphere` | `StaticMeshActor` (with Sphere mesh) |
| `Cylinder` | `StaticMeshActor` (with Cylinder mesh) |
| `Cone` | `StaticMeshActor` (with Cone mesh) |
| `Plane` / `Floor` | `StaticMeshActor` (with Plane mesh) |
| `PointLight` | `PointLight` |
| `SpotLight` | `SpotLight` |
| `DirectionalLight` | `DirectionalLight` |
| `Camera` | `CameraActor` |
| `PlayerStart` | `PlayerStart` |
| `SkyLight` | `SkyLight` |
| `ExponentialHeightFog` | `ExponentialHeightFog` |
| Any UE class name | Loaded and spawned dynamically |

## Plugin File Structure

```
unreal/
  README.md
  unreal_server_init.py        # Backwards-compatible startup shim
  game_engine_mcp_unreal/
    __init__.py                # Public lifecycle exports
    config.py                  # Host, port, auto-start settings
    log_buffer.py              # Captured stdout/stderr buffer
    protocol.py                # JSON response helpers
    registry.py                # Command registration and metadata
    server.py                  # TCP server lifecycle and dispatch
    ue_helpers.py              # Shared Unreal serialization/adapters
    unreal_import.py           # Unreal-only import guard
    commands/
      actors.py                # Actor lookup, spawn, transform, visibility
      assets.py                # Content browser and asset operations
      editor.py                # Play mode, console, code, viewport, selection
      properties.py            # Actor/component property access
      scene.py                 # Level and hierarchy operations
```

## Unreal Engine Python APIs Used

The plugin uses these UE Python modules:

- `unreal.EditorLevelLibrary` - Level/actor operations
- `unreal.EditorAssetLibrary` - Asset operations
- `unreal.EditorLoadingAndSavingUtils` - Level loading/saving
- `unreal.SystemLibrary` - Play mode, execute console commands
- `unreal.EditorFilterLibrary` - Actor filtering
- `unreal.LevelEditorSubsystem` - Level editor operations
- `unreal.UnrealEditorSubsystem` - Editor state
- `unreal.AssetRegistryHelpers` - Asset discovery

## Troubleshooting

### "No module named 'unreal'" error

- Ensure the **Python Editor Script Plugin** is enabled in your project.
- Restart the editor after enabling.

### "Failed to start server" error

- Port 9878 may be in use. Change the port in `unreal_server_init.py`.
- Only one instance can bind to a port at a time.

### MCP server cannot connect

- Check the UE Output Log for `[GameEngineMCP]` messages.
- Verify host and port match between the plugin and `engines.local.yaml`.
- If connecting from a different machine (e.g., Docker), set host to `0.0.0.0`.

### Some commands return "not available"

- Ensure the **Editor Scripting Utilities** plugin is enabled.
- Some APIs require UE 5.1+ or newer.

## Security

The TCP server binds to `127.0.0.1` (localhost only) by default. Only change this if you understand the implications -- anyone with network access to the configured port can execute editor commands.
