"""Bridge registry -- manages live editor connections.

Holds one :class:`EditorBridge` per engine and provides lifecycle
methods (auto-connect on startup, disconnect on shutdown).
"""

from __future__ import annotations

import logging
from typing import Any

from .base import EditorBridge

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Concrete bridge registry (lazy imports to avoid hard dependency on all)
# ---------------------------------------------------------------------------

_BRIDGE_CLASSES: dict[str, str] = {
    "unity": "src.bridges.unity_bridge:UnityBridge",
    "unreal": "src.bridges.unreal_bridge:UnrealBridge",
    "godot": "src.bridges.godot_bridge:GodotBridge",
}


def _import_bridge_class(dotted_path: str) -> type[EditorBridge]:
    """Import a bridge class from a ``module.path:ClassName`` string."""
    module_path, class_name = dotted_path.rsplit(":", 1)
    import importlib

    module = importlib.import_module(module_path)
    return getattr(module, class_name)


class BridgeRegistry:
    """Singleton registry of active editor bridges."""

    _instance: BridgeRegistry | None = None

    def __init__(self) -> None:
        self._bridges: dict[str, EditorBridge] = {}

    @classmethod
    def instance(cls) -> BridgeRegistry:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_bridge(self, engine: str) -> EditorBridge | None:
        """Return the bridge for *engine*, or ``None`` if not instantiated."""
        return self._bridges.get(engine.lower())

    async def connect(
        self, engine: str, host: str = "127.0.0.1", port: int = 0
    ) -> bool:
        """Create (if needed) and connect a bridge for *engine*."""
        engine = engine.lower()
        bridge = self._bridges.get(engine)
        if bridge is None:
            bridge = self._create_bridge(engine)
            if bridge is None:
                logger.error("No bridge implementation for engine '%s'", engine)
                return False
            self._bridges[engine] = bridge

        if bridge.connected:
            return True

        return await bridge.connect(host, port)

    async def disconnect(self, engine: str) -> None:
        """Disconnect and remove the bridge for *engine*."""
        bridge = self._bridges.pop(engine.lower(), None)
        if bridge is not None:
            await bridge.disconnect()

    async def disconnect_all(self) -> None:
        """Disconnect all active bridges."""
        for engine in list(self._bridges):
            await self.disconnect(engine)

    def status(self) -> dict[str, dict[str, Any]]:
        """Return connection status for all registered bridges."""
        result: dict[str, dict[str, Any]] = {}
        for engine, bridge in self._bridges.items():
            result[engine] = {
                "connected": bridge.connected,
                "host": bridge.host,
                "port": bridge.port,
                "engine": bridge.engine,
            }
        return result

    async def auto_connect(self, config: dict[str, dict[str, Any]]) -> None:
        """Auto-connect bridges from configuration.

        *config* is a dict like ``{"unity": {"host": "...", "port": 9877, "auto_connect": True}}``.
        """
        for engine, settings in config.items():
            if settings.get("auto_connect"):
                host = settings.get("host", "127.0.0.1")
                port = settings.get("port", 0)
                if port:
                    logger.info(
                        "Auto-connecting %s bridge to %s:%s", engine, host, port
                    )
                    await self.connect(engine, host, port)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _create_bridge(engine: str) -> EditorBridge | None:
        """Instantiate a bridge for *engine* by lazy import."""
        class_path = _BRIDGE_CLASSES.get(engine)
        if class_path is None:
            return None
        try:
            cls = _import_bridge_class(class_path)
            return cls()
        except Exception as exc:
            logger.error("Failed to create bridge for %s: %s", engine, exc)
            return None
