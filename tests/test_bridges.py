"""Tests for the bridge infrastructure: protocol, base bridge, registry, config."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.bridges.protocol import (
    McpResponse,
    decode_response,
    encode_command,
    next_request_id,
)
from src.bridges.base import (
    EditorBridge,
    EditorCommandError,
    NotConnectedError,
)
from src.bridges.registry import BridgeRegistry
from src.bridges.unity_bridge import UnityBridge
from src.bridge_config import load_bridge_config


# ---------------------------------------------------------------------------
# Protocol tests
# ---------------------------------------------------------------------------


class TestProtocol:
    def test_encode_command_basic(self):
        req_id, raw = encode_command("ping")
        parsed = json.loads(raw.decode("utf-8").strip())
        assert parsed["command"] == "ping"
        assert parsed["id"] == req_id
        assert "params" not in parsed

    def test_encode_command_with_params(self):
        req_id, raw = encode_command(
            "get_console_logs", {"count": 20, "level": "error"}
        )
        parsed = json.loads(raw.decode("utf-8").strip())
        assert parsed["command"] == "get_console_logs"
        assert parsed["params"]["count"] == 20
        assert parsed["params"]["level"] == "error"

    def test_encode_command_ends_with_newline(self):
        _, raw = encode_command("ping")
        assert raw.endswith(b"\n")

    def test_decode_response_ok(self):
        resp = decode_response(b'{"id": 1, "status": "ok", "data": {"key": "value"}}')
        assert resp.id == 1
        assert resp.status == "ok"
        assert resp.data["key"] == "value"
        assert resp.error is None

    def test_decode_response_error(self):
        resp = decode_response(b'{"id": 2, "status": "error", "error": "bad"}')
        assert resp.id == 2
        assert resp.status == "error"
        assert resp.error == "bad"

    def test_decode_response_empty_raises(self):
        with pytest.raises(ValueError, match="Empty response"):
            decode_response(b"")

    def test_decode_response_malformed_raises(self):
        with pytest.raises(json.JSONDecodeError):
            decode_response(b"not json")

    def test_next_request_id_monotonic(self):
        id1 = next_request_id()
        id2 = next_request_id()
        assert id2 > id1


# ---------------------------------------------------------------------------
# Mock bridge for testing base class behavior
# ---------------------------------------------------------------------------


class MockBridge(EditorBridge):
    engine = "mock"

    def __init__(self):
        super().__init__()
        self._sent_commands: list[tuple[str, dict]] = []
        self._mock_connected = False

    async def connect(self, host: str = "127.0.0.1", port: int = 0) -> bool:
        self._host = host
        self._port = port
        self._connected = True
        self._mock_connected = True
        return True

    async def disconnect(self) -> None:
        self._connected = False
        self._mock_connected = False

    async def send_command(self, command: str, params=None, timeout=30.0):
        if not self._mock_connected:
            raise NotConnectedError("Not connected")
        self._sent_commands.append((command, params or {}))

        # Simulate responses
        if command == "ping":
            return McpResponse(0, "ok", {"status": "alive", "engine": "mock"})
        if command == "get_console_logs":
            return McpResponse(
                0, "ok", {"logs": [{"level": "error", "message": "test error"}]}
            )
        if command == "get_scene_hierarchy":
            return McpResponse(0, "ok", {"name": "Main", "children": []})
        if command == "play":
            return McpResponse(0, "ok", {})
        if command == "get_object":
            return McpResponse(
                0, "ok", {"name": "TestObj", "type": "GameObject", "components": []}
            )
        if command == "set_property":
            return McpResponse(0, "ok", {})
        if command == "get_properties":
            return McpResponse(0, "ok", {"properties": {"mass": 1.0}})
        if command == "list_assets":
            return McpResponse(0, "ok", {"assets": [{"name": "Main", "type": "Scene"}]})
        if command == "take_screenshot":
            return McpResponse(0, "ok", {"image_base64": "fakebase64data"})
        if command == "execute_code":
            return McpResponse(0, "ok", {"output": "hello"})
        if command == "error_test":
            return McpResponse(0, "error", error="Test error")
        return McpResponse(0, "ok", {})


def _run(coro):
    import asyncio

    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Base bridge tests
# ---------------------------------------------------------------------------


class TestEditorBridge:
    def test_connect(self):
        bridge = MockBridge()
        assert not bridge.connected
        ok = _run(bridge.connect("127.0.0.1", 9877))
        assert ok
        assert bridge.connected
        assert bridge.host == "127.0.0.1"
        assert bridge.port == 9877

    def test_disconnect(self):
        bridge = MockBridge()
        _run(bridge.connect())
        assert bridge.connected
        _run(bridge.disconnect())
        assert not bridge.connected

    def test_ping(self):
        bridge = MockBridge()
        _run(bridge.connect())
        data = _run(bridge.ping())
        assert data["status"] == "alive"
        assert data["engine"] == "mock"

    def test_get_console_logs(self):
        bridge = MockBridge()
        _run(bridge.connect())
        logs = _run(bridge.get_console_logs(count=10, level="error"))
        assert len(logs) == 1
        assert logs[0]["level"] == "error"

    def test_play(self):
        bridge = MockBridge()
        _run(bridge.connect())
        assert _run(bridge.play())

    def test_get_object(self):
        bridge = MockBridge()
        _run(bridge.connect())
        data = _run(bridge.get_object("TestObj"))
        assert data["name"] == "TestObj"

    def test_set_property(self):
        bridge = MockBridge()
        _run(bridge.connect())
        assert _run(bridge.set_property("Player", "Transform", "position", [1, 2, 3]))

    def test_get_properties(self):
        bridge = MockBridge()
        _run(bridge.connect())
        data = _run(bridge.get_properties("Player", "Rigidbody"))
        assert "mass" in data["properties"]

    def test_list_assets(self):
        bridge = MockBridge()
        _run(bridge.connect())
        data = _run(bridge.list_assets())
        assert len(data["assets"]) == 1

    def test_take_screenshot(self):
        bridge = MockBridge()
        _run(bridge.connect())
        b64 = _run(bridge.take_screenshot())
        assert b64 == "fakebase64data"

    def test_execute_code(self):
        bridge = MockBridge()
        _run(bridge.connect())
        data = _run(bridge.execute_code("print('hi')"))
        assert data["output"] == "hello"

    def test_error_response_raises(self):
        bridge = MockBridge()
        _run(bridge.connect())

        # Override mock to return error for a convenience method
        async def _error_send(command, params=None, timeout=30.0):
            from src.bridges.protocol import McpResponse

            return McpResponse(0, "error", error="Test error")

        bridge.send_command = _error_send
        with pytest.raises(EditorCommandError, match="Test error"):
            _run(bridge.ping())

    def test_not_connected_raises(self):
        bridge = MockBridge()
        with pytest.raises(NotConnectedError):
            _run(bridge.send_command("ping"))


class TestUnityBridgeCommands:
    def test_unity_specific_methods_send_expected_commands(self):
        bridge = UnityBridge()
        sent: list[tuple[str, dict]] = []

        async def _send(command, params=None, timeout=30.0):
            sent.append((command, params or {}))
            return McpResponse(0, "ok", {"ok": True})

        bridge.send_command = _send

        assert _run(bridge.open_scene("Assets/Main.unity"))["ok"]
        assert _run(bridge.add_component("Player", "Rigidbody"))["ok"]
        assert _run(bridge.get_asset_dependencies("Assets/Main.unity"))["ok"]
        assert sent == [
            ("open_scene", {"path": "Assets/Main.unity", "mode": "single"}),
            ("add_component", {"path": "Player", "component": "Rigidbody"}),
            (
                "get_asset_dependencies",
                {"path": "Assets/Main.unity", "recursive": True},
            ),
        ]


# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestBridgeRegistry:
    def setup_method(self):
        BridgeRegistry._instance = None

    def test_connect_creates_bridge(self):
        reg = BridgeRegistry.instance()
        mock_bridge = MockBridge()
        with patch.object(BridgeRegistry, "_create_bridge", return_value=mock_bridge):
            ok = _run(reg.connect("unity", "127.0.0.1", 9877))
            assert ok
            assert reg.get_bridge("unity") is mock_bridge

    def test_disconnect(self):
        reg = BridgeRegistry.instance()
        mock_bridge = MockBridge()
        _run(mock_bridge.connect())
        reg._bridges["unity"] = mock_bridge
        _run(reg.disconnect("unity"))
        assert not mock_bridge.connected
        assert reg.get_bridge("unity") is None

    def test_disconnect_all(self):
        reg = BridgeRegistry.instance()
        b1 = MockBridge()
        b2 = MockBridge()
        _run(b1.connect())
        _run(b2.connect())
        reg._bridges["unity"] = b1
        reg._bridges["godot"] = b2
        _run(reg.disconnect_all())
        assert not b1.connected
        assert not b2.connected
        assert len(reg._bridges) == 0

    def test_status(self):
        reg = BridgeRegistry.instance()
        b1 = MockBridge()
        b1._host = "127.0.0.1"
        b1._port = 9877
        b1._connected = True
        reg._bridges["unity"] = b1
        status = reg.status()
        assert "unity" in status
        assert status["unity"]["connected"] is True
        assert status["unity"]["port"] == 9877

    def test_auto_connect(self):
        reg = BridgeRegistry.instance()
        config = {
            "unity": {"host": "127.0.0.1", "port": 9877, "auto_connect": True},
            "unreal": {"host": "127.0.0.1", "port": 9878, "auto_connect": False},
        }
        with patch.object(BridgeRegistry, "_create_bridge", return_value=MockBridge()):
            _run(reg.auto_connect(config))
            assert reg.get_bridge("unity") is not None
            assert reg.get_bridge("unreal") is None

    def test_get_bridge_nonexistent(self):
        reg = BridgeRegistry.instance()
        assert reg.get_bridge("nonexistent") is None


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


class TestBridgeConfig:
    def test_load_from_nonexistent_file(self):
        config = load_bridge_config(Path("/nonexistent/engines.local.yaml"))
        assert "unity" in config
        assert config["unity"]["port"] == 9877
        assert config["unity"]["auto_connect"] is False

    def test_load_from_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(
                "bridges:\n"
                "  unity:\n"
                "    host: '192.168.1.100'\n"
                "    port: 9999\n"
                "    auto_connect: true\n"
                "  godot:\n"
                "    host: '127.0.0.1'\n"
                "    port: 8080\n"
                "    auto_connect: false\n"
            )
            f.flush()
            config = load_bridge_config(Path(f.name))

        os.unlink(f.name)

        assert config["unity"]["host"] == "192.168.1.100"
        assert config["unity"]["port"] == 9999
        assert config["unity"]["auto_connect"] is True
        assert config["godot"]["port"] == 8080
        # Unreal should get defaults
        assert config["unreal"]["port"] == 9878

    def test_load_from_yaml_no_bridges_key(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("engines:\n  - engine: unity\n")
            f.flush()
            config = load_bridge_config(Path(f.name))

        os.unlink(f.name)
        assert config["unity"]["port"] == 9877  # default

    def test_load_from_yaml_invalid_bridges_type(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("bridges: [1, 2, 3]\n")
            f.flush()
            config = load_bridge_config(Path(f.name))

        os.unlink(f.name)
        assert config["unity"]["port"] == 9877  # defaults
