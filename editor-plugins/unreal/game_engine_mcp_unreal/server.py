"""TCP server lifecycle and JSON command dispatch."""

from __future__ import annotations

import json
import socketserver
import threading

from . import log_buffer
from .config import HOST, PORT
from .protocol import make_error
from .registry import COMMANDS
from .unreal_import import unreal

_server: socketserver.ThreadingTCPServer | None = None
_server_thread: threading.Thread | None = None
_server_lock = threading.Lock()


class McpRequestHandler(socketserver.StreamRequestHandler):
    """Handle newline-delimited JSON requests for one TCP client."""

    def handle(self) -> None:
        unreal.log(f"[GameEngineMCP] Client connected: {self.client_address}")
        try:
            while True:
                raw = self.rfile.readline()
                if not raw:
                    break
                text = raw.decode("utf-8").strip()
                if not text:
                    continue
                self.wfile.write(dispatch(text).encode("utf-8"))
                self.wfile.flush()
        except ConnectionError:
            pass
        except Exception as exc:
            unreal.log_warning(f"[GameEngineMCP] Handler error: {exc}")
        finally:
            unreal.log("[GameEngineMCP] Client disconnected")


class ThreadedTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def dispatch(raw_json: str) -> str:
    req_id = 0
    try:
        request = json.loads(raw_json)
        req_id = int(request.get("id", 0))
        command = request.get("command", "")
        params = request.get("params", {})
        if not isinstance(params, dict):
            return make_error(req_id, "Request params must be an object")

        handler = COMMANDS.get(command)
        if handler is None:
            return make_error(req_id, f"Unknown command: {command}")
        return handler(req_id, params)
    except json.JSONDecodeError as exc:
        return make_error(req_id, f"Invalid JSON: {exc}")
    except Exception as exc:
        return make_error(req_id, f"Internal error: {exc}")


def start_server(host: str = HOST, port: int = PORT) -> None:
    """Start the TCP command server. Safe to call repeatedly."""
    global _server, _server_thread

    with _server_lock:
        if _server is not None:
            unreal.log_warning("[GameEngineMCP] Server already running")
            return

        try:
            _server = ThreadedTCPServer((host, port), McpRequestHandler)
            _server_thread = threading.Thread(
                target=_server.serve_forever,
                daemon=True,
                name="GameEngineMCP-Server",
            )
            _server_thread.start()
            log_buffer.install_stream_hooks()
            unreal.log(f"[GameEngineMCP] Server started on {host}:{port}")
        except Exception as exc:
            _server = None
            _server_thread = None
            unreal.log_error(f"[GameEngineMCP] Failed to start server: {exc}")


def stop_server() -> None:
    """Stop the TCP command server and restore Python streams."""
    global _server, _server_thread

    with _server_lock:
        if _server is None:
            return
        try:
            _server.shutdown()
            _server.server_close()
        except Exception as exc:
            unreal.log_warning(f"[GameEngineMCP] Error during shutdown: {exc}")
        finally:
            _server = None
            _server_thread = None
            log_buffer.restore_stream_hooks()
            unreal.log("[GameEngineMCP] Server stopped")


def restart_server() -> None:
    stop_server()
    start_server()
