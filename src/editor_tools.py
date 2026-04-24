"""MCP tools for live editor interaction.

These tools connect to running game engine editors (Unity, Unreal, Godot)
through TCP bridges and expose editor operations to AI assistants.

If no editor is connected, tools return a helpful error message rather
than crashing the documentation MCP server.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from mcp.server.fastmcp import FastMCP

from .bridges.base import EditorCommandError, NotConnectedError
from .bridges.registry import BridgeRegistry

logger = logging.getLogger(__name__)


def _registry() -> BridgeRegistry:
    return BridgeRegistry.instance()


def _bridge(engine: str):
    bridge = _registry().get_bridge(engine)
    if bridge is None or not bridge.connected:
        return None
    return bridge


def _run(coro):
    """Run an async coroutine from sync context (MCP tools are sync)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=60)
    else:
        return asyncio.run(coro)


def _not_connected_msg(engine: str) -> str:
    return (
        f"No {engine} editor is currently connected. "
        f"Use editor_connect(engine='{engine}') to connect first."
    )


def _handle_error(exc: Exception, engine: str, action: str) -> str:
    if isinstance(exc, NotConnectedError):
        return _not_connected_msg(engine)
    if isinstance(exc, EditorCommandError):
        return f"Editor error during {action}: {exc}"
    return f"Unexpected error during {action}: {exc}"


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_editor_tools(mcp: FastMCP) -> None:
    """Register all live-editor MCP tools on the given FastMCP app."""

    @mcp.tool()
    def editor_connect(
        engine: str,
        host: str = "127.0.0.1",
        port: int = 0,
    ) -> str:
        """Connect to a running game engine editor.

        The editor must have the GameEngineMCP plugin installed and running.

        Default ports: unity=9877, unreal=9878, godot=9879

        Examples:
          - engine='unity'
          - engine='unreal', host='192.168.1.50', port=9878
        """
        engine = engine.strip().lower()
        reg = _registry()

        if not port:
            from .bridge_config import load_bridge_config

            config = load_bridge_config()
            port = config.get(engine, {}).get("port", 0)

        if not port:
            defaults = {"unity": 9877, "unreal": 9878, "godot": 9879}
            port = defaults.get(engine, 0)

        if not port:
            return f"Unknown engine '{engine}'. Supported: unity, unreal, godot"

        try:
            ok = _run(reg.connect(engine, host, port))
        except Exception as exc:
            return f"Connection failed: {exc}"

        if ok:
            return f"Connected to {engine} editor at {host}:{port}"
        return f"Failed to connect to {engine} editor at {host}:{port}. Is the editor running with the plugin installed?"

    @mcp.tool()
    def editor_disconnect(engine: str) -> str:
        """Disconnect from a game engine editor.

        Examples:
          - engine='unity'
        """
        engine = engine.strip().lower()
        _run(_registry().disconnect(engine))
        return f"Disconnected from {engine} editor"

    @mcp.tool()
    def editor_status() -> str:
        """Show connection status for all editor bridges."""
        status = _registry().status()
        if not status:
            return "No editor bridges registered. Use editor_connect to connect."

        lines = ["Editor Bridge Status", "=" * 25]
        for engine, info in sorted(status.items()):
            state = "CONNECTED" if info["connected"] else "disconnected"
            lines.append(f"  {engine}: {state} ({info['host']}:{info['port']})")
        return "\n".join(lines)

    @mcp.tool()
    def editor_play(engine: str) -> str:
        """Start play mode in the editor.

        Examples:
          - engine='unity'
          - engine='unreal'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.play())
            return f"{engine} editor: play mode started"
        except Exception as exc:
            return _handle_error(exc, engine, "play")

    @mcp.tool()
    def editor_pause(engine: str) -> str:
        """Pause play mode in the editor.

        Examples:
          - engine='unity'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.pause())
            return f"{engine} editor: play mode paused"
        except Exception as exc:
            return _handle_error(exc, engine, "pause")

    @mcp.tool()
    def editor_stop(engine: str) -> str:
        """Stop play mode in the editor.

        Examples:
          - engine='unity'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.stop())
            return f"{engine} editor: play mode stopped"
        except Exception as exc:
            return _handle_error(exc, engine, "stop")

    @mcp.tool()
    def editor_get_console(
        engine: str,
        count: int = 50,
        level: str | None = None,
    ) -> str:
        """Get console logs from the editor.

        Examples:
          - engine='unity', count=20
          - engine='unity', level='error'
          - engine='unreal', count=100, level='warning'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            logs = _run(bridge.get_console_logs(count=count, level=level))
            if not logs:
                return f"No console logs found in {engine} editor."
            lines = [f"{engine} Console Logs ({len(logs)} entries):"]
            for entry in logs:
                lvl = entry.get("level", "log").upper()
                msg = entry.get("message", "")
                lines.append(f"  [{lvl}] {msg}")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "get_console")

    @mcp.tool()
    def editor_clear_console(engine: str) -> str:
        """Clear the console in the editor.

        Examples:
          - engine='unity'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.clear_console())
            return f"{engine} console cleared"
        except Exception as exc:
            return _handle_error(exc, engine, "clear_console")

    @mcp.tool()
    def editor_get_scene_hierarchy(engine: str) -> str:
        """Get the full scene hierarchy from the editor.

        Returns the scene tree as structured text with indentation showing
        parent-child relationships.

        Examples:
          - engine='unity'
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_scene_hierarchy())
            return _format_hierarchy(data)
        except Exception as exc:
            return _handle_error(exc, engine, "get_scene_hierarchy")

    @mcp.tool()
    def editor_get_object(engine: str, path: str) -> str:
        """Get detailed information about a scene object including all components.

        Examples:
          - engine='unity', path='Main Camera'
          - engine='unreal', path='Player'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_object(path))
            return _format_object(data)
        except Exception as exc:
            return _handle_error(exc, engine, "get_object")

    @mcp.tool()
    def editor_create_object(
        engine: str,
        name: str,
        type: str | None = None,
        parent: str | None = None,
    ) -> str:
        """Create a new object in the scene.

        Examples:
          - engine='unity', name='Player'
          - engine='unity', name='Enemy', type='Cube', parent='Enemies'
          - engine='godot', name='Player', type='CharacterBody3D'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.create_object(name, type=type, parent=parent))
            return f"Created object: {_format_object_brief(data)}"
        except Exception as exc:
            return _handle_error(exc, engine, "create_object")

    @mcp.tool()
    def editor_delete_object(engine: str, path: str) -> str:
        """Delete an object from the scene.

        Examples:
          - engine='unity', path='OldEnemy'
          - engine='unreal', path='DebugCube'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.delete_object(path))
            return f"Deleted object '{path}' from {engine} scene"
        except Exception as exc:
            return _handle_error(exc, engine, "delete_object")

    @mcp.tool()
    def editor_set_property(
        engine: str,
        path: str,
        component: str,
        property: str,
        value: Any,
    ) -> str:
        """Set a property on a component of a scene object.

        Examples:
          - engine='unity', path='Player', component='Transform', property='position', value=[0, 5, 0]
          - engine='unity', path='Player', component='Rigidbody', property='mass', value=5.0
          - engine='godot', path='Player/Sprite', component='Sprite2D', property='visible', value=False
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.set_property(path, component, property, value))
            return f"Set {path}.{component}.{property} = {value!r}"
        except Exception as exc:
            return _handle_error(exc, engine, "set_property")

    @mcp.tool()
    def editor_get_properties(
        engine: str,
        path: str,
        component: str | None = None,
    ) -> str:
        """Get serialized properties of a scene object's component(s).

        Examples:
          - engine='unity', path='Player', component='Transform'
          - engine='unity', path='Player'  (all components)
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_properties(path, component=component))
            lines = [f"Properties of '{path}'"]
            if component:
                lines.append(f"  Component: {component}")
            for key, val in data.get("properties", {}).items():
                lines.append(f"  {key}: {val}")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "get_properties")

    @mcp.tool()
    def editor_move_object(
        engine: str,
        path: str,
        parent: str | None = None,
        position: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> str:
        """Move, rotate, scale, or reparent a scene object.

        Examples:
          - engine='unity', path='Player', position=[10, 0, 5]
          - engine='unity', path='Player', rotation=[0, 90, 0]
          - engine='unity', path='HealthBar', parent='UI/Canvas'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(
                bridge.move_object(
                    path,
                    parent=parent,
                    position=position,
                    rotation=rotation,
                    scale=scale,
                )
            )
            parts = [f"Updated '{path}'"]
            if parent:
                parts.append(f"parent={parent}")
            if position:
                parts.append(f"position={position}")
            if rotation:
                parts.append(f"rotation={rotation}")
            if scale:
                parts.append(f"scale={scale}")
            return ", ".join(parts)
        except Exception as exc:
            return _handle_error(exc, engine, "move_object")

    @mcp.tool()
    def editor_list_assets(engine: str, path: str = "Assets") -> str:
        """List assets in the project.

        Examples:
          - engine='unity', path='Assets/Scenes'
          - engine='unreal', path='/Game/Characters'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.list_assets(path))
            assets = data.get("assets", [])
            if not assets:
                return f"No assets found at '{path}'"
            lines = [f"Assets in '{path}' ({len(assets)} items):"]
            for asset in assets:
                name = asset.get("name", "?")
                asset_type = asset.get("type", "")
                lines.append(f"  {name} ({asset_type})")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "list_assets")

    @mcp.tool()
    def editor_save_scene(engine: str, path: str | None = None) -> str:
        """Save the current scene.

        Examples:
          - engine='unity'
          - engine='unity', path='Assets/Scenes/Level2.unity'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.save_scene(path=path))
            target = path or "current path"
            return f"Scene saved to {target}"
        except Exception as exc:
            return _handle_error(exc, engine, "save_scene")

    @mcp.tool()
    def editor_take_screenshot(engine: str) -> str:
        """Capture a screenshot of the editor viewport.

        Returns a base64-encoded PNG image.

        Examples:
          - engine='unity'
          - engine='unreal'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            b64 = _run(bridge.take_screenshot())
            if not b64:
                return "Screenshot returned empty image"
            return f"Screenshot captured ({len(b64)} chars base64 PNG). Data: {b64[:100]}..."
        except Exception as exc:
            return _handle_error(exc, engine, "take_screenshot")

    @mcp.tool()
    def editor_execute_code(engine: str, code: str, language: str | None = None) -> str:
        """Execute code in the editor.

        Use with caution -- this runs arbitrary code in the editor process.

        Examples:
          - engine='unity', code='UnityEngine.Debug.Log("Hello from MCP")', language='csharp'
          - engine='godot', code='print("Hello")', language='gdscript'
          - engine='unreal', code='print("Hello")', language='python'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.execute_code(code, language=language))
            output = data.get("output", "")
            error = data.get("error", "")
            parts = ["Code execution result:"]
            if output:
                parts.append(f"  Output: {output}")
            if error:
                parts.append(f"  Error: {error}")
            if not output and not error:
                parts.append("  (no output)")
            return "\n".join(parts)
        except Exception as exc:
            return _handle_error(exc, engine, "execute_code")

    @mcp.tool()
    def editor_play_custom_scene(engine: str, path: str) -> str:
        """Play a specific scene in the editor (not the main scene).

        Examples:
          - engine='godot', path='res://scenes/level_2.tscn'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.play_custom_scene(path))
            return f"{engine} editor: playing scene '{path}'"
        except Exception as exc:
            return _handle_error(exc, engine, "play_custom_scene")

    @mcp.tool()
    def editor_save_all_scenes(engine: str) -> str:
        """Save all open scenes in the editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.save_all_scenes())
            return f"{engine} editor: all scenes saved"
        except Exception as exc:
            return _handle_error(exc, engine, "save_all_scenes")

    @mcp.tool()
    def editor_restart(engine: str, save: bool = True) -> str:
        """Restart the editor. Optionally save all scenes before restarting.

        Examples:
          - engine='godot', save=True
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.restart_editor(save=save))
            return f"{engine} editor: restarting (save={save})"
        except Exception as exc:
            return _handle_error(exc, engine, "restart_editor")

    @mcp.tool()
    def editor_get_paths(engine: str) -> str:
        """Get editor paths (cache, config, data, project settings directories).

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_editor_paths())
            lines = [f"{engine} Editor Paths:"]
            for key in ["cacheDir", "configDir", "dataDir", "projectSettingsDir"]:
                if key in data:
                    lines.append(f"  {key}: {data[key]}")
            lines.append(f"  isSelfContained: {data.get('isSelfContained', False)}")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "get_editor_paths")

    @mcp.tool()
    def editor_get_plugin_state(engine: str, plugin: str) -> str:
        """Check whether an editor plugin is enabled.

        Examples:
          - engine='godot', plugin='game_engine_mcp'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.is_plugin_enabled(plugin))
            state = "enabled" if data.get("enabled") else "disabled"
            return f"Plugin '{plugin}' is {state}"
        except Exception as exc:
            return _handle_error(exc, engine, "is_plugin_enabled")

    @mcp.tool()
    def editor_set_plugin_state(engine: str, plugin: str, enabled: bool) -> str:
        """Enable or disable an editor plugin.

        Examples:
          - engine='godot', plugin='some_plugin', enabled=True
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.set_plugin_enabled(plugin, enabled))
            state = "enabled" if enabled else "disabled"
            return f"Plugin '{plugin}' {state}"
        except Exception as exc:
            return _handle_error(exc, engine, "set_plugin_enabled")

    @mcp.tool()
    def editor_get_snap_settings(engine: str) -> str:
        """Get the editor's snap/grid settings for 3D nodes.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_snap_settings())
            lines = [f"{engine} Snap Settings:"]
            lines.append(f"  translateSnap: {data.get('node3dTranslateSnap')}")
            lines.append(f"  rotateSnap: {data.get('node3dRotateSnap')}")
            lines.append(f"  scaleSnap: {data.get('node3dScaleSnap')}")
            lines.append(f"  snapEnabled: {data.get('node3dSnapEnabled')}")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "get_snap_settings")

    @mcp.tool()
    def editor_push_toast(engine: str, message: str, severity: int = 0) -> str:
        """Show a notification toast in the editor.

        Severity: 0=info, 1=warning, 2=error.

        Examples:
          - engine='godot', message='Build complete', severity=0
          - engine='godot', message='Missing texture', severity=1
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.push_toast(message, severity))
            return f"Toast shown: '{message}' (severity={severity})"
        except Exception as exc:
            return _handle_error(exc, engine, "push_toast")

    @mcp.tool()
    def editor_navigate_filesystem(engine: str, path: str) -> str:
        """Navigate the editor's filesystem dock to a specific path.

        Examples:
          - engine='godot', path='res://textures'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.navigate_filesystem(path))
            return f"Filesystem dock navigated to '{path}'"
        except Exception as exc:
            return _handle_error(exc, engine, "navigate_filesystem")

    @mcp.tool()
    def editor_scan_filesystem(engine: str) -> str:
        """Trigger a full filesystem rescan in the editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.scan_filesystem())
            return f"{engine} editor: filesystem scan started"
        except Exception as exc:
            return _handle_error(exc, engine, "scan_filesystem")

    @mcp.tool()
    def editor_reimport_files(engine: str, files: list[str]) -> str:
        """Force reimport of specific asset files.

        Examples:
          - engine='godot', files=['res://icon.svg', 'res://textures/ground.png']
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.reimport_files(files))
            return f"Reimporting {len(files)} files"
        except Exception as exc:
            return _handle_error(exc, engine, "reimport_files")

    @mcp.tool()
    def editor_get_file_type(engine: str, path: str) -> str:
        """Get the resource type of a file without loading it.

        Examples:
          - engine='godot', path='res://icon.svg'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_file_type(path))
            return f"File '{path}' type: {data.get('type', 'unknown')}"
        except Exception as exc:
            return _handle_error(exc, engine, "get_file_type")

    @mcp.tool()
    def editor_get_filesystem_directory(engine: str, path: str = "res://") -> str:
        """List files and subdirectories in the editor's resource filesystem.

        Returns richer data than list_assets (includes file types and import status).

        Examples:
          - engine='godot', path='res://scenes'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_filesystem_directory(path))
            lines = [f"Directory: {data.get('path', path)}"]
            for f in data.get("files", []):
                imp = " [import ok]" if f.get("importValid") else ""
                lines.append(f"  {f.get('name', '?')} ({f.get('type', '?')}){imp}")
            for d in data.get("subdirs", []):
                lines.append(f"  {d.get('name', '?')}/ ({d.get('fileCount', 0)} files)")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "get_filesystem_directory")

    @mcp.tool()
    def editor_get_current_script(engine: str) -> str:
        """Get the currently open script in the editor's script editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_current_script())
            path = data.get("path", "")
            if not path:
                return "No script currently open"
            return f"Current script: {path}"
        except Exception as exc:
            return _handle_error(exc, engine, "get_current_script")

    @mcp.tool()
    def editor_get_open_scripts(engine: str) -> str:
        """List all scripts currently open in the editor's script editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_open_scripts())
            scripts = data.get("scripts", [])
            if not scripts:
                return "No scripts open"
            lines = [f"Open scripts ({len(scripts)}):"]
            for s in scripts:
                lines.append(f"  {s.get('path', '?')}")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "get_open_scripts")

    @mcp.tool()
    def editor_get_unsaved_scripts(engine: str) -> str:
        """Get a list of unsaved script files in the editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_unsaved_script_files())
            unsaved = data.get("unsavedFiles", [])
            if not unsaved:
                return "No unsaved scripts"
            return f"Unsaved scripts: {', '.join(unsaved)}"
        except Exception as exc:
            return _handle_error(exc, engine, "get_unsaved_script_files")

    @mcp.tool()
    def editor_save_all_scripts(engine: str) -> str:
        """Save all open scripts in the editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.save_all_scripts())
            return f"{engine} editor: all scripts saved"
        except Exception as exc:
            return _handle_error(exc, engine, "save_all_scripts")

    @mcp.tool()
    def editor_reload_scripts(engine: str) -> str:
        """Reload all open script files from disk in the editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.reload_open_files())
            return f"{engine} editor: open files reloaded"
        except Exception as exc:
            return _handle_error(exc, engine, "reload_open_files")

    @mcp.tool()
    def editor_get_breakpoints(engine: str) -> str:
        """Get all breakpoints set in the editor.

        Examples:
          - engine='godot'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            data = _run(bridge.get_breakpoints())
            bps = data.get("breakpoints", [])
            if not bps:
                return "No breakpoints set"
            lines = [f"Breakpoints ({len(bps)}):"]
            for bp in bps:
                lines.append(f"  {bp}")
            return "\n".join(lines)
        except Exception as exc:
            return _handle_error(exc, engine, "get_breakpoints")

    @mcp.tool()
    def editor_goto_line(engine: str, line: int) -> str:
        """Jump to a specific line in the currently open script.

        Examples:
          - engine='godot', line=42
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.goto_line(line))
            return f"Jumped to line {line}"
        except Exception as exc:
            return _handle_error(exc, engine, "goto_line")

    @mcp.tool()
    def editor_inspect_object(engine: str, path: str, for_property: str = "", inspector_only: bool = False) -> str:
        """Show an object in the editor's inspector panel.

        Examples:
          - engine='godot', path='Player'
          - engine='godot', path='Player', for_property='position'
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.inspect_object(path, for_property=for_property, inspector_only=inspector_only))
            return f"Inspecting '{path}'"
        except Exception as exc:
            return _handle_error(exc, engine, "inspect_object")

    @mcp.tool()
    def editor_set_object_edited(engine: str, path: str, edited: bool = True) -> str:
        """Mark an object as edited (dirty) or unedited in the editor.

        Examples:
          - engine='godot', path='Player', edited=True
        """
        bridge = _bridge(engine)
        if not bridge:
            return _not_connected_msg(engine)
        try:
            _run(bridge.set_object_edited(path, edited))
            state = "edited" if edited else "unedited"
            return f"'{path}' marked as {state}"
        except Exception as exc:
            return _handle_error(exc, engine, "set_object_edited")


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------


def _format_hierarchy(data: dict[str, Any], indent: int = 0) -> str:
    """Format a scene hierarchy tree as indented text."""
    lines: list[str] = []
    name = data.get("name", "?")
    obj_type = data.get("type", "")
    prefix = "  " * indent
    type_tag = f" ({obj_type})" if obj_type else ""
    lines.append(f"{prefix}{name}{type_tag}")
    for child in data.get("children", []):
        lines.append(_format_hierarchy(child, indent + 1))
    return "\n".join(lines)


def _format_object(data: dict[str, Any]) -> str:
    """Format an object's details as text."""
    lines: list[str] = []
    name = data.get("name", "?")
    obj_type = data.get("type", "")
    active = data.get("active", True)
    lines.append(f"Object: {name} ({obj_type})")
    lines.append(f"  Active: {active}")

    components = data.get("components", [])
    if components:
        lines.append(f"  Components ({len(components)}):")
        for comp in components:
            comp_name = comp.get("name", "?")
            comp_type = comp.get("type", "")
            lines.append(f"    - {comp_name} ({comp_type})")
            for key, val in comp.get("properties", {}).items():
                lines.append(f"      {key}: {val}")
    return "\n".join(lines)


def _format_object_brief(data: dict[str, Any]) -> str:
    """Format a brief one-line object summary."""
    name = data.get("name", "?")
    obj_type = data.get("type", "")
    return f"{name} ({obj_type})"
