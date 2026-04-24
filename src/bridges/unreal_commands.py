"""Unreal Engine editor bridge -- TCP client for the GameEngineMCP UE plugin.

Unreal-specific commands live here as methods on :class:`UnrealBridge`.
The shared base commands (play, stop, scene hierarchy, object CRUD, etc.)
are inherited from :class:`EditorBridge`.

The UE plugin runs as a Python TCP server inside the Unreal Editor
(``unreal_server_init.py``) and speaks the shared JSON wire protocol.
"""

from __future__ import annotations

from typing import Any

from .base import EditorBridge


class UnrealBridge(EditorBridge):
    """Bridge to a running Unreal Editor via the GameEngineMCP TCP plugin.

    The UE plugin listens on a configurable port (default 9878) and
    speaks the shared JSON wire protocol defined in :mod:`protocol`.

    In addition to the shared commands inherited from :class:`EditorBridge`,
    this class exposes Unreal-specific APIs for level management, actor
    operations, asset management, viewport control, selection, and more.
    """

    engine: str = "unreal"

    # ------------------------------------------------------------------
    # Level management
    # ------------------------------------------------------------------

    async def new_level(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("new_level", {"path": path})
        self._check_error(resp)
        return resp.data

    async def open_level(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("open_level", {"path": path})
        self._check_error(resp)
        return resp.data

    async def save_all_levels(self) -> dict[str, Any]:
        resp = await self.send_command("save_all_levels")
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Actor operations
    # ------------------------------------------------------------------

    async def find_actors(
        self,
        name: str | None = None,
        class_type: str | None = None,
        tag: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"limit": limit}
        if name:
            params["name"] = name
        if class_type:
            params["class_type"] = class_type
        if tag:
            params["tag"] = tag
        resp = await self.send_command("find_actors", params)
        self._check_error(resp)
        return resp.data

    async def duplicate_actor(
        self, path: str, name: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"path": path}
        if name:
            params["name"] = name
        resp = await self.send_command("duplicate_actor", params)
        self._check_error(resp)
        return resp.data

    async def set_actor_visible(self, path: str, visible: bool) -> dict[str, Any]:
        resp = await self.send_command(
            "set_actor_visible", {"path": path, "visible": visible}
        )
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Asset operations
    # ------------------------------------------------------------------

    async def get_asset(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("get_asset", {"path": path})
        self._check_error(resp)
        return resp.data

    async def delete_asset(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("delete_asset", {"path": path})
        self._check_error(resp)
        return resp.data

    async def move_asset(self, source: str, destination: str) -> dict[str, Any]:
        resp = await self.send_command(
            "move_asset", {"source": source, "destination": destination}
        )
        self._check_error(resp)
        return resp.data

    async def rename_asset(self, path: str, name: str) -> dict[str, Any]:
        resp = await self.send_command("rename_asset", {"path": path, "name": name})
        self._check_error(resp)
        return resp.data

    async def duplicate_asset(self, source: str, destination: str) -> dict[str, Any]:
        resp = await self.send_command(
            "duplicate_asset", {"source": source, "destination": destination}
        )
        self._check_error(resp)
        return resp.data

    async def import_asset(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("import_asset", {"path": path})
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Viewport
    # ------------------------------------------------------------------

    async def get_viewport_camera(self) -> dict[str, Any]:
        resp = await self.send_command("get_viewport_camera")
        self._check_error(resp)
        return resp.data

    async def set_viewport_camera(
        self,
        location: list[float] | None = None,
        rotation: list[float] | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if location:
            params["location"] = location
        if rotation:
            params["rotation"] = rotation
        resp = await self.send_command("set_viewport_camera", params)
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    async def get_selection(self) -> dict[str, Any]:
        resp = await self.send_command("get_selection")
        self._check_error(resp)
        return resp.data

    async def set_selection(self, paths: list[str]) -> dict[str, Any]:
        resp = await self.send_command("set_selection", {"paths": paths})
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Content / project
    # ------------------------------------------------------------------

    async def get_content_directory(self, path: str = "/Game/") -> dict[str, Any]:
        resp = await self.send_command("get_content_directory", {"path": path})
        self._check_error(resp)
        return resp.data

    async def get_project_dir(self) -> dict[str, Any]:
        resp = await self.send_command("get_project_dir")
        self._check_error(resp)
        return resp.data
