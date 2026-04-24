"""Backwards-compatible startup shim for the modular Unreal plugin.

Wire protocol:
Request:  {"id": 1, "command": "ping", "params": {}}\n
Response: {"id": 1, "status": "ok", "data": {...}}\n
Error:    {"id": 1, "status": "error", "error": "message"}\n
"""

from __future__ import annotations

import sys
from pathlib import Path

_PLUGIN_DIR = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
if str(_PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(_PLUGIN_DIR))

from game_engine_mcp_unreal.config import AUTO_START, HOST, PORT  # noqa: E402
from game_engine_mcp_unreal.server import restart_server, start_server, stop_server  # noqa: E402

__all__ = [
    "AUTO_START",
    "HOST",
    "PORT",
    "restart_server",
    "start_server",
    "stop_server",
]

if AUTO_START:
    start_server()
