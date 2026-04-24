"""In-editor log capture used by console commands."""

from __future__ import annotations

import sys
import threading

LOG_BUFFER_MAX = 2000

_log_buffer: list[dict[str, str]] = []
_log_buffer_lock = threading.Lock()
_orig_stdout_write = sys.stdout.write
_orig_stderr_write = sys.stderr.write


def capture_log(message: str) -> None:
    _append("log", message)


def capture_error(message: str) -> None:
    _append("error", message)


def read_logs(count: int = 50, level: str | None = None) -> list[dict[str, str]]:
    with _log_buffer_lock:
        logs = list(_log_buffer)
    if level:
        normalized_level = level.lower()
        logs = [entry for entry in logs if entry["level"] == normalized_level]
    return logs[-count:]


def clear_logs() -> None:
    with _log_buffer_lock:
        _log_buffer.clear()


def install_stream_hooks() -> None:
    sys.stdout.write = _stdout_hook
    sys.stderr.write = _stderr_hook


def restore_stream_hooks() -> None:
    sys.stdout.write = _orig_stdout_write
    sys.stderr.write = _orig_stderr_write


def _append(level: str, message: str) -> None:
    text = str(message).rstrip()
    if not text:
        return
    with _log_buffer_lock:
        _log_buffer.append({"level": level, "message": text})
        if len(_log_buffer) > LOG_BUFFER_MAX:
            del _log_buffer[:-LOG_BUFFER_MAX]


def _stdout_hook(text: str) -> int:
    capture_log(text)
    return _orig_stdout_write(text)


def _stderr_hook(text: str) -> int:
    capture_error(text)
    return _orig_stderr_write(text)
