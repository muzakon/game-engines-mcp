# Game Engine MCP - Unity Plugin

A Unity Editor plugin that opens a TCP command port for live editor interaction via the [game-engine-mcp](../../) Python server. Lets AI assistants read console errors, manipulate scenes, edit Inspector properties, control play mode, and more.

## Requirements

- Unity 2021.3 or newer
- The `com.unity.nuget.newtonsoft-json` package (auto-resolved as a dependency)

## Installation

### Option A: Copy into project (simplest)

1. Copy the entire `unity/` folder into your Unity project:

```
YourUnityProject/
  Assets/
    Editor/
      GameEngineMCP/        <-- copy the contents of Editor/GameEngineMCP/ here
        McpServer.cs
        CommandRouter.cs
        MiniJson.cs
        Commands/
        Models/
        UI/
```

2. Copy `package.json` alongside the `Editor/` folder, or skip it if installing manually (Newtonsoft.Json is already included in most Unity versions).

3. Unity will auto-compile the scripts on the next editor refresh.

### Option B: Unity Package Manager (local package)

1. Move or clone this `unity/` folder to a location on disk (e.g. next to your Unity project).

2. Open Unity: **Window > Package Manager**.

3. Click **+** (top-left) > **Add package from disk...**.

4. Select the `package.json` file inside the `unity/` folder.

5. Unity will resolve the Newtonsoft.Json dependency automatically.

### Option C: Git URL (if you publish the repo)

1. Open **Window > Package Manager**.
2. Click **+** > **Add package from Git URL...**.
3. Enter the URL pointing to this `unity/` directory.

## Setup

### 1. Configure the plugin

Open **Tools > Game Engine MCP > Settings** in the Unity Editor:

- **Host**: The interface to bind to (default: `127.0.0.1`).
- **Port**: The TCP port (default: `9877`).
- **Auto Start**: Start the TCP server automatically when Unity loads (default: on).

Settings are saved to `ProjectSettings/GameEngineMCP.json`.

You can also start/stop/restart the server manually:

- **Tools > Game Engine MCP > Start Server**
- **Tools > Game Engine MCP > Stop Server**
- **Tools > Game Engine MCP > Restart Server**

### 2. Configure the Python MCP server

In your `engines.local.yaml` (at the game-engine-mcp project root):

```yaml
bridges:
  unity:
    host: "127.0.0.1"
    port: 9877
    auto_connect: true
```

### 3. Start the MCP server

```bash
cd /path/to/game-engine-mcp
uv run python scripts/run_server.py
```

The MCP server will auto-connect to the Unity plugin on startup (if `auto_connect: true`).

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

Once connected, the following tools work with `engine='unity'`:

| Tool | Example |
|------|---------|
| `editor_connect` | `editor_connect(engine='unity')` |
| `editor_status` | `editor_status()` |
| `editor_get_console` | `editor_get_console(engine='unity', count=20, level='error')` |
| `editor_clear_console` | `editor_clear_console(engine='unity')` |
| `editor_get_scene_hierarchy` | `editor_get_scene_hierarchy(engine='unity')` |
| `editor_get_object` | `editor_get_object(engine='unity', path='Main Camera')` |
| `editor_create_object` | `editor_create_object(engine='unity', name='Player', type='Cube')` |
| `editor_delete_object` | `editor_delete_object(engine='unity', path='OldEnemy')` |
| `editor_set_property` | `editor_set_property(engine='unity', path='Player', component='Transform', property='position', value=[0,5,0])` |
| `editor_get_properties` | `editor_get_properties(engine='unity', path='Player', component='Rigidbody')` |
| `editor_move_object` | `editor_move_object(engine='unity', path='Player', position=[10,0,5])` |
| `editor_play` | `editor_play(engine='unity')` |
| `editor_pause` | `editor_pause(engine='unity')` |
| `editor_stop` | `editor_stop(engine='unity')` |
| `editor_list_assets` | `editor_list_assets(engine='unity', path='Assets/Scenes')` |
| `editor_save_scene` | `editor_save_scene(engine='unity')` |
| `editor_take_screenshot` | `editor_take_screenshot(engine='unity')` |
| `editor_execute_code` | `editor_execute_code(engine='unity', code='Debug.Log("hi")')` |
| `editor_disconnect` | `editor_disconnect(engine='unity')` |

The Unity bridge also implements lower-level Unity-specific commands for clients that call the bridge directly:

- Scene: `new_scene`, `open_scene`, `close_scene`, `get_open_scenes`, `save_all_scenes`, `mark_scene_dirty`
- Editor: `execute_menu_item`, `repaint_editor`, `get_selection`, `set_selection`, `ping_object`
- GameObject: `duplicate_object`, `set_object_active`, `add_component`, `remove_component`
- Assets: `get_asset`, `import_asset`, `refresh_assets`, `create_folder`, `delete_asset`, `move_asset`, `copy_asset`, `rename_asset`, `get_asset_dependencies`, `reveal_asset`

## Plugin File Structure

```
unity/
  package.json                  # Unity package manifest
  Editor/
    GameEngineMCP/
      McpServer.cs              # TCP listener, lifecycle, settings
      CommandRouter.cs          # Command dispatch
      UnityMcpUtility.cs        # Shared object/path/value helpers
      Commands/
        EditorCommands.cs       # ping, play, pause, stop, info, run_tests
        ConsoleCommands.cs      # get_console_logs, clear_console
        SceneCommands.cs        # hierarchy, active scene, save
        ObjectCommands.cs       # get/create/delete/move objects
        PropertyCommands.cs     # get/set serialized properties
        AssetCommands.cs        # list assets
        ScreenshotCommands.cs   # viewport capture
        CodeCommands.cs         # execute C# or Python
      Models/
        McpRequest.cs           # Incoming command model
        McpResponse.cs          # Outgoing response model
      UI/
        McpSettingsWindow.cs    # Editor window (Tools > Game Engine MCP > Settings)
```

## Troubleshooting

### Plugin does not appear in Unity

- Ensure the files are under an `Editor/` folder (Unity only compiles editor scripts from folders named `Editor`).
- Check the Console for compilation errors.

### "Failed to start" error

- The port may be in use. Change it in **Tools > Game Engine MCP > Settings**.
- On macOS/Linux, ports below 1024 require elevated privileges. Use a port above 1024.

### MCP server cannot connect

- Verify Unity shows "Running" in **Tools > Game Engine MCP > Settings**.
- Check that the host and port match between Unity settings and `engines.local.yaml`.
- If Unity is on a different machine, set the host to `0.0.0.0` in Unity settings and use the machine's IP in `engines.local.yaml`.

### Newtonsoft.Json not found

- Install via Package Manager: `com.unity.nuget.newtonsoft-json` version 3.2.2 or later.
- If installing by copying files (Option A), Newtonsoft.Json is already included in Unity 2021.3+ as a built-in package.

## Security

The TCP server binds to `127.0.0.1` by default (localhost only). Only change this if you understand the implications -- anyone with network access to the configured port can execute editor commands.
