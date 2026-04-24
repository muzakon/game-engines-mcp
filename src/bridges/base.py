"""Abstract base class for editor bridges.

Every concrete bridge (Unity, Unreal, Godot) inherits from
:class:`EditorBridge` and implements the TCP client that talks
to the engine-specific editor plugin.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC
from typing import Any

from .protocol import McpResponse, encode_command, decode_response

logger = logging.getLogger(__name__)


class NotConnectedError(ConnectionError):
    """Raised when a command is sent without an active editor connection."""


class EditorBridge(ABC):
    """Base class for a live editor connection.

    Subclasses must implement :meth:`_open_connection` and
    :meth:`_close_connection` to manage the underlying socket.
    The default :meth:`send_command` handles the JSON wire protocol
    over a raw TCP stream.
    """

    engine: str = ""

    def __init__(self) -> None:
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._host: str = ""
        self._port: int = 0
        self._connected: bool = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def host(self) -> str:
        return self._host

    @property
    def port(self) -> int:
        return self._port

    async def connect(self, host: str = "127.0.0.1", port: int = 0) -> bool:
        """Open a TCP connection to the editor plugin.

        Returns ``True`` on success.
        """
        if self._connected:
            await self.disconnect()

        self._host = host
        self._port = port
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5.0
            )
            self._connected = True
            logger.info("Connected to %s editor at %s:%s", self.engine, host, port)
            return True
        except Exception as exc:
            self._connected = False
            logger.warning(
                "Failed to connect to %s at %s:%s: %s", self.engine, host, port, exc
            )
            return False

    async def disconnect(self) -> None:
        """Close the TCP connection."""
        if self._writer is not None:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
        self._reader = None
        self._writer = None
        self._connected = False
        logger.info("Disconnected from %s editor", self.engine)

    # ------------------------------------------------------------------
    # Wire protocol
    # ------------------------------------------------------------------

    async def send_command(
        self,
        command: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> McpResponse:
        """Send a JSON command and wait for the matching response.

        Raises :class:`NotConnectedError` if the bridge is not connected.
        Raises :class:`asyncio.TimeoutError` if the editor does not reply
        within *timeout* seconds.
        """
        if not self._connected or self._writer is None or self._reader is None:
            raise NotConnectedError(f"Not connected to {self.engine} editor")

        req_id, raw = encode_command(command, params)
        self._writer.write(raw)
        await self._writer.drain()

        # Read lines until we find the matching response ID.
        while True:
            line_bytes = await asyncio.wait_for(
                self._reader.readline(), timeout=timeout
            )
            if not line_bytes:
                self._connected = False
                raise NotConnectedError("Editor closed the connection")

            try:
                resp = decode_response(line_bytes)
            except ValueError as exc:
                logger.warning("Malformed response from %s: %s", self.engine, exc)
                continue

            if resp.id == req_id:
                return resp

            # Out-of-order response (e.g. async console log push).
            # Log and keep reading.
            logger.debug(
                "Out-of-order response %d (expected %d) from %s",
                resp.id,
                req_id,
                self.engine,
            )

    # ------------------------------------------------------------------
    # Convenience command methods
    # ------------------------------------------------------------------

    async def ping(self) -> dict[str, Any]:
        resp = await self.send_command("ping")
        self._check_error(resp)
        return resp.data

    async def get_editor_info(self) -> dict[str, Any]:
        resp = await self.send_command("get_editor_info")
        self._check_error(resp)
        return resp.data

    async def play(self) -> bool:
        resp = await self.send_command("play")
        self._check_error(resp)
        return resp.status == "ok"

    async def pause(self) -> bool:
        resp = await self.send_command("pause")
        self._check_error(resp)
        return resp.status == "ok"

    async def stop(self) -> bool:
        resp = await self.send_command("stop")
        self._check_error(resp)
        return resp.status == "ok"

    async def get_console_logs(
        self, count: int = 50, level: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"count": count}
        if level:
            params["level"] = level
        resp = await self.send_command("get_console_logs", params)
        self._check_error(resp)
        return resp.data.get("logs", [])

    async def clear_console(self) -> bool:
        resp = await self.send_command("clear_console")
        self._check_error(resp)
        return resp.status == "ok"

    async def get_scene_hierarchy(self) -> dict[str, Any]:
        resp = await self.send_command("get_scene_hierarchy")
        self._check_error(resp)
        return resp.data

    async def get_active_scene(self) -> dict[str, Any]:
        resp = await self.send_command("get_active_scene")
        self._check_error(resp)
        return resp.data

    async def save_scene(self, path: str | None = None) -> bool:
        params: dict[str, Any] = {}
        if path:
            params["path"] = path
        resp = await self.send_command("save_scene", params)
        self._check_error(resp)
        return resp.status == "ok"

    async def get_object(self, path: str) -> dict[str, Any]:
        resp = await self.send_command("get_object", {"path": path})
        self._check_error(resp)
        return resp.data

    async def create_object(
        self,
        name: str,
        type: str | None = None,
        parent: str | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"name": name}
        if type:
            params["type"] = type
        if parent:
            params["parent"] = parent
        resp = await self.send_command("create_object", params)
        self._check_error(resp)
        return resp.data

    async def delete_object(self, path: str) -> bool:
        resp = await self.send_command("delete_object", {"path": path})
        self._check_error(resp)
        return resp.status == "ok"

    async def move_object(
        self,
        path: str,
        parent: str | None = None,
        position: list[float] | None = None,
        rotation: list[float] | None = None,
        scale: list[float] | None = None,
    ) -> bool:
        params: dict[str, Any] = {"path": path}
        if parent:
            params["parent"] = parent
        if position:
            params["position"] = position
        if rotation:
            params["rotation"] = rotation
        if scale:
            params["scale"] = scale
        resp = await self.send_command("move_object", params)
        self._check_error(resp)
        return resp.status == "ok"

    async def get_properties(
        self, path: str, component: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"path": path}
        if component:
            params["component"] = component
        resp = await self.send_command("get_properties", params)
        self._check_error(resp)
        return resp.data

    async def set_property(
        self, path: str, component: str, property: str, value: Any
    ) -> bool:
        resp = await self.send_command(
            "set_property",
            {
                "path": path,
                "component": component,
                "property": property,
                "value": value,
            },
        )
        self._check_error(resp)
        return resp.status == "ok"

    async def set_properties(
        self, path: str, component: str, properties: dict[str, Any]
    ) -> bool:
        resp = await self.send_command(
            "set_properties",
            {"path": path, "component": component, "properties": properties},
        )
        self._check_error(resp)
        return resp.status == "ok"

    async def list_assets(self, path: str = "Assets") -> dict[str, Any]:
        resp = await self.send_command("list_assets", {"path": path})
        self._check_error(resp)
        return resp.data

    async def take_screenshot(self) -> str:
        """Capture the editor viewport. Returns a base64-encoded PNG."""
        resp = await self.send_command("take_screenshot")
        self._check_error(resp)
        return resp.data.get("image_base64", "")

    async def execute_code(
        self, code: str, language: str | None = None
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"code": code}
        if language:
            params["language"] = language
        resp = await self.send_command("execute_code", params)
        self._check_error(resp)
        return resp.data

    async def run_tests(self, test_mode: str = "edit") -> dict[str, Any]:
        resp = await self.send_command("run_tests", {"test_mode": test_mode})
        self._check_error(resp)
        return resp.data

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_error(resp: McpResponse) -> None:
        if resp.status == "error":
            raise EditorCommandError(resp.error or "Unknown editor error")


class EditorCommandError(RuntimeError):
    """Raised when the editor returns an error response."""
