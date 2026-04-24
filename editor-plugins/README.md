# Editor Plugins

TCP command port plugins for live game engine editor interaction with the [game-engine-mcp](../) server.

Each plugin opens a TCP server inside the editor that speaks a shared JSON wire protocol. The Python MCP server connects as a client and exposes editor operations as MCP tools to AI assistants.

## Available Plugins

| Engine | Status | Port | Directory |
|--------|--------|------|-----------|
| **Unity** | Ready | 9877 | [unity/](unity/) |
| **Unreal Engine** | Ready | 9878 | [unreal/](unreal/) |
| **Godot** | Ready | 9879 | [godot/](godot/) |

## Wire Protocol

All plugins use the same JSON-over-TCP protocol:

```
Request:  {"id": 1, "command": "get_console_logs", "params": {"count": 20}}
Response: {"id": 1, "status": "ok", "data": {"logs": [...]}}
Error:    {"id": 1, "status": "error", "error": "No active scene"}
```

Messages are newline-delimited. Each response echoes back the request `id` for matching.

## Supported Commands

| Category | Command | Description |
|----------|---------|-------------|
| **Editor** | `ping` | Heartbeat / version check |
| | `get_editor_info` | Engine version, project name, platform |
| | `play` / `pause` / `stop` | Control play mode |
| | `run_tests` | Run editor or play mode tests |
| **Console** | `get_console_logs` | Get logs with level filtering |
| | `clear_console` | Clear the console |
| **Scene** | `get_scene_hierarchy` | Full scene tree as nested JSON |
| | `get_active_scene` | Active scene name/path |
| | `save_scene` | Save current scene |
| **Objects** | `get_object` | Get object with all components |
| | `create_object` | Create object (Empty, Cube, Sphere, etc.) |
| | `delete_object` | Delete object by path |
| | `move_object` | Reparent, position, rotate, scale |
| **Properties** | `get_properties` | Read serialized properties |
| | `set_property` | Set a single property value |
| | `set_properties` | Batch set multiple properties |
| **Assets** | `list_assets` | List project assets |
| **Screenshots** | `take_screenshot` | Capture viewport as base64 PNG |
| **Code** | `execute_code` | Execute C# or Python in editor |

## Configuration

Bridge connection settings go in `engines.local.yaml` at the project root:

```yaml
bridges:
  unity:
    host: "127.0.0.1"
    port: 9877
    auto_connect: true   # connect on MCP server startup
  unreal:
    host: "127.0.0.1"
    port: 9878
    auto_connect: false
  godot:
    host: "127.0.0.1"
    port: 9879
    auto_connect: false
```

## Architecture

```
AI Client (Cursor, Claude, etc.)
        |
        | MCP Protocol
        v
game-engine-mcp (Python)
        |
        | TCP + JSON wire protocol
        v
Editor Plugin (C# / C++ / GDScript)
        |
        | Editor APIs
        v
Game Engine Editor (Unity / Unreal / Godot)
```
