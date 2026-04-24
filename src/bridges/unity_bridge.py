"""Unity editor bridge -- TCP client for the GameEngineMCP Unity plugin.

Unity-specific commands should be added here as methods on
:class:`UnityBridge`.  The shared base commands (play, stop, scene
hierarchy, object CRUD, etc.) are inherited from :class:`EditorBridge`.
"""

from __future__ import annotations

from typing import Any

from .base import EditorBridge


class UnityBridge(EditorBridge):
    """Bridge to a running Unity Editor via the GameEngineMCP TCP plugin.

    The Unity plugin listens on a configurable port (default 9877) and
    speaks the shared JSON wire protocol defined in :mod:`protocol`.

    Add Unity-specific command methods here as the Unity plugin grows.
    """

    engine: str = "unity"

    # ------------------------------------------------------------------
    # Scene management
    # ------------------------------------------------------------------

    async def new_scene(self, setup: str = "default", mode: str = "single") -> dict[str, Any]:
        resp = await self.send_command("new_scene", {"setup": setup, "mode": mode})
        self._check_error(resp)
        return resp.data

    async def open_scene(self, path: str, mode: str = "single") -> dict[str, Any]:
        resp = await self.send_command("open_scene", {"path": path, "mode": mode})
        self._check_error(resp)
        return resp.data

    async def close_scene(self, path: str = "", remove_scene: bool = True) -> dict[str, Any]:
        resp = await self.send_command(
            "close_scene", {"path": path, "removeScene": remove_scene}
        )
        self._check_error(resp)
        return resp.data

    async def get_open_scenes(self) -> dict[str, Any]:
        resp = await self.send_command("get_open_scenes")
        self._check_error(resp)
        return resp.data

    async def save_all_scenes(self) -> dict[str, Any]:
        resp = await self.send_command("save_all_scenes")
        self._check_error(resp)
        return resp.data

    async def mark_scene_dirty(self, path: str = "") -> dict[str, Any]:
        resp = await self.send_command("mark_scene_dirty", {"path": path})
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Editor state and selection
    # ------------------------------------------------------------------

    async def execute_menu_item(self, menu_item: str) -> dict[str, Any]:
        resp = await self.send_command("execute_menu_item", {"menuItem": menu_item})
        self._check_error(resp)
        return resp.data

    async def repaint_editor(self) -> dict[str, Any]:
        resp = await self.send_command("repaint_editor")
        self._check_error(resp)
        return resp.data

    async def get_selection(self) -> dict[str, Any]:
        resp = await self.send_command("get_selection")
        self._check_error(resp)
        return resp.data

    async def set_selection(
        self, path: str | None = None, paths: list[str] | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if path:
            params["path"] = path
        if paths:
            params["paths"] = paths
        resp = await self.send_command("set_selection", params)
        self._check_error(resp)
        return resp.data

    async def ping_object(
        self, path: str | None = None, instance_id: int | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if path:
            params["path"] = path
        if instance_id is not None:
            params["instanceId"] = instance_id
        resp = await self.send_command("ping_object", params)
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # GameObject / component operations
    # ------------------------------------------------------------------

    async def duplicate_object(
        self, path: str, name: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"path": path}
        if name:
            params["name"] = name
        resp = await self.send_command("duplicate_object", params)
        self._check_error(resp)
        return resp.data

    async def set_object_active(self, path: str, active: bool) -> dict[str, Any]:
        resp = await self.send_command(
            "set_object_active", {"path": path, "active": active}
        )
        self._check_error(resp)
        return resp.data

    async def add_component(self, path: str, component: str) -> dict[str, Any]:
        resp = await self.send_command(
            "add_component", {"path": path, "component": component}
        )
        self._check_error(resp)
        return resp.data

    async def remove_component(self, path: str, component: str) -> dict[str, Any]:
        resp = await self.send_command(
            "remove_component", {"path": path, "component": component}
        )
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # AssetDatabase operations
    # ------------------------------------------------------------------

    async def get_asset(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("get_asset", {"path": path})
        self._check_error(resp)
        return resp.data

    async def import_asset(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("import_asset", {"path": path})
        self._check_error(resp)
        return resp.data

    async def refresh_assets(self) -> dict[str, Any]:
        resp = await self.send_command("refresh_assets")
        self._check_error(resp)
        return resp.data

    async def create_folder(self, parent: str, name: str) -> dict[str, Any]:
        resp = await self.send_command("create_folder", {"parent": parent, "name": name})
        self._check_error(resp)
        return resp.data

    async def delete_asset(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("delete_asset", {"path": path})
        self._check_error(resp)
        return resp.data

    async def move_asset(self, source: str, destination: str) -> dict[str, Any]:
        resp = await self.send_command(
            "move_asset", {"from": source, "to": destination}
        )
        self._check_error(resp)
        return resp.data

    async def copy_asset(self, source: str, destination: str) -> dict[str, Any]:
        resp = await self.send_command(
            "copy_asset", {"from": source, "to": destination}
        )
        self._check_error(resp)
        return resp.data

    async def rename_asset(self, path: str, name: str) -> dict[str, Any]:
        resp = await self.send_command("rename_asset", {"path": path, "name": name})
        self._check_error(resp)
        return resp.data

    async def get_asset_dependencies(
        self, path: str, recursive: bool = True
    ) -> dict[str, Any]:
        resp = await self.send_command(
            "get_asset_dependencies", {"path": path, "recursive": recursive}
        )
        self._check_error(resp)
        return resp.data

    async def reveal_asset(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("reveal_asset", {"path": path})
        self._check_error(resp)
        return resp.data
