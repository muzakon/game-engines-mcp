"""JSON response helpers for the GameEngineMCP wire protocol."""

from __future__ import annotations

import json
from typing import Any


def make_ok(req_id: int, data: dict[str, Any] | None = None) -> str:
    response: dict[str, Any] = {"id": req_id, "status": "ok"}
    if data:
        response["data"] = data
    return json.dumps(response, separators=(",", ":")) + "\n"


def make_error(req_id: int, error: str, data: dict[str, Any] | None = None) -> str:
    response: dict[str, Any] = {"id": req_id, "status": "error", "error": error}
    if data:
        response["data"] = data
    return json.dumps(response, separators=(",", ":")) + "\n"
