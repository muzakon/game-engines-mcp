"""Command registry for the Unreal Editor bridge."""

from __future__ import annotations

from typing import Any, Callable

CommandHandler = Callable[[int, dict[str, Any]], str]
