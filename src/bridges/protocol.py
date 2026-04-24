"""JSON wire protocol for editor command port communication.

Every message is a single JSON object terminated by ``\\n``.
Requests carry a unique ``id`` that responses echo back.

Request::

    {"id": 1, "command": "get_console_logs", "params": {"count": 20}}

Response::

    {"id": 1, "status": "ok", "data": {"logs": [...]}}
    {"id": 1, "status": "error", "error": "No active scene"}
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from typing import Any


@dataclass
class McpRequest:
    """A command sent to an engine editor."""

    command: str
    params: dict[str, Any] = field(default_factory=dict)
    id: int = 0


@dataclass
class McpResponse:
    """A response received from an engine editor."""

    id: int
    status: str  # "ok" or "error"
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


_next_id: int = 0
_id_lock = threading.Lock()


def next_request_id() -> int:
    """Return a monotonically-increasing request ID (thread-safe)."""
    global _next_id
    with _id_lock:
        _next_id += 1
        return _next_id


def encode_command(
    command: str, params: dict[str, Any] | None = None
) -> tuple[int, bytes]:
    """Encode a command into the wire format.

    Returns ``(request_id, raw_bytes)`` where *raw_bytes* ends with ``\\n``.
    """
    req_id = next_request_id()
    payload: dict[str, Any] = {"id": req_id, "command": command}
    if params:
        payload["params"] = params
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
    return req_id, raw


def decode_response(raw: bytes) -> McpResponse:
    """Decode a raw bytes payload into an :class:`McpResponse`.

    Raises :class:`ValueError` on malformed JSON.
    """
    text = raw.decode("utf-8").strip()
    if not text:
        raise ValueError("Empty response from editor")
    obj = json.loads(text)
    return McpResponse(
        id=obj.get("id", 0),
        status=obj.get("status", "error"),
        data=obj.get("data", {}),
        error=obj.get("error"),
    )
