"""Godot-specific editor bridge commands.

:class:`GodotBridge` extends the shared :class:`EditorBridge` with
commands that only the Godot editor plugin implements (scene management,
plugin control, filesystem operations, script editor introspection, etc.).
"""

from __future__ import annotations

from typing import Any

from .base import EditorBridge


class GodotBridge(EditorBridge):
    """Bridge to a running Godot Editor via the GameEngineMCP TCP addon.

    The Godot addon listens on a configurable port (default 9879) and
    speaks the shared JSON wire protocol.

    In addition to the shared commands inherited from :class:`EditorBridge`,
    this class exposes Godot-specific APIs for scene management, plugin
    control, filesystem operations, script editor introspection, and more.
    """

    engine: str = "godot"

    # ------------------------------------------------------------------
    # Scene / playback
    # ------------------------------------------------------------------

    async def play_custom_scene(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("play_custom_scene", {"path": path})
        self._check_error(resp)
        return resp.data

    async def save_all_scenes(self) -> dict[str, Any]:
        resp = await self.send_command("save_all_scenes")
        self._check_error(resp)
        return resp.data

    async def restart_editor(self, save: bool = True) -> dict[str, Any]:
        resp = await self.send_command("restart_editor", {"save": save})
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Editor state
    # ------------------------------------------------------------------

    async def get_current_feature_profile(self) -> dict[str, Any]:
        resp = await self.send_command("get_current_feature_profile")
        self._check_error(resp)
        return resp.data

    async def get_editor_paths(self) -> dict[str, Any]:
        resp = await self.send_command("get_editor_paths")
        self._check_error(resp)
        return resp.data

    async def is_plugin_enabled(self, plugin: str) -> dict[str, Any]:
        resp = await self.send_command("is_plugin_enabled", {"plugin": plugin})
        self._check_error(resp)
        return resp.data

    async def set_plugin_enabled(self, plugin: str, enabled: bool) -> dict[str, Any]:
        resp = await self.send_command("set_plugin_enabled", {"plugin": plugin, "enabled": enabled})
        self._check_error(resp)
        return resp.data

    async def get_editor_theme(self) -> dict[str, Any]:
        resp = await self.send_command("get_editor_theme")
        self._check_error(resp)
        return resp.data

    async def get_editor_language(self) -> dict[str, Any]:
        resp = await self.send_command("get_editor_language")
        self._check_error(resp)
        return resp.data

    async def is_multi_window_enabled(self) -> dict[str, Any]:
        resp = await self.send_command("is_multi_window_enabled")
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Object / inspector
    # ------------------------------------------------------------------

    async def inspect_object(self, path: str, for_property: str = "", inspector_only: bool = False) -> dict[str, Any]:
        params: dict[str, Any] = {"path": path}
        if for_property:
            params["for_property"] = for_property
        if inspector_only:
            params["inspector_only"] = inspector_only
        resp = await self.send_command("inspect_object", params)
        self._check_error(resp)
        return resp.data

    async def set_object_edited(self, path: str, edited: bool) -> dict[str, Any]:
        resp = await self.send_command("set_object_edited", {"path": path, "edited": edited})
        self._check_error(resp)
        return resp.data

    async def is_object_edited(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("is_object_edited", {"path": path})
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Snap settings
    # ------------------------------------------------------------------

    async def get_snap_settings(self) -> dict[str, Any]:
        resp = await self.send_command("get_snap_settings")
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Notifications
    # ------------------------------------------------------------------

    async def push_toast(self, message: str, severity: int = 0) -> dict[str, Any]:
        resp = await self.send_command("push_toast", {"message": message, "severity": severity})
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Filesystem
    # ------------------------------------------------------------------

    async def navigate_filesystem(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("navigate_filesystem", {"path": path})
        self._check_error(resp)
        return resp.data

    async def scan_filesystem(self) -> dict[str, Any]:
        resp = await self.send_command("scan_filesystem")
        self._check_error(resp)
        return resp.data

    async def scan_sources(self) -> dict[str, Any]:
        resp = await self.send_command("scan_sources")
        self._check_error(resp)
        return resp.data

    async def reimport_files(self, files: list[str]) -> dict[str, Any]:
        resp = await self.send_command("reimport_files", {"files": files})
        self._check_error(resp)
        return resp.data

    async def get_file_type(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("get_file_type", {"path": path})
        self._check_error(resp)
        return resp.data

    async def get_filesystem_directory(self, path: str = "") -> dict[str, Any]:
        params: dict[str, Any] = {}
        if path:
            params["path"] = path
        resp = await self.send_command("get_filesystem_directory", params)
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Script editor
    # ------------------------------------------------------------------

    async def get_current_script(self) -> dict[str, Any]:
        resp = await self.send_command("get_current_script")
        self._check_error(resp)
        return resp.data

    async def get_open_scripts(self) -> dict[str, Any]:
        resp = await self.send_command("get_open_scripts")
        self._check_error(resp)
        return resp.data

    async def get_unsaved_script_files(self) -> dict[str, Any]:
        resp = await self.send_command("get_unsaved_script_files")
        self._check_error(resp)
        return resp.data

    async def save_all_scripts(self) -> dict[str, Any]:
        resp = await self.send_command("save_all_scripts")
        self._check_error(resp)
        return resp.data

    async def reload_open_files(self) -> dict[str, Any]:
        resp = await self.send_command("reload_open_files")
        self._check_error(resp)
        return resp.data

    async def get_breakpoints(self) -> dict[str, Any]:
        resp = await self.send_command("get_breakpoints")
        self._check_error(resp)
        return resp.data

    async def goto_line(self, line: int) -> dict[str, Any]:
        resp = await self.send_command("goto_line", {"line": line})
        self._check_error(resp)
        return resp.data
