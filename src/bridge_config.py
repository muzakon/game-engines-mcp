"""Load bridge connection settings from ``engines.local.yaml``.

The ``bridges`` top-level key in that file holds per-engine connection
parameters::

    bridges:
      unity:
        host: "127.0.0.1"
        port: 9877
        auto_connect: true
      unreal:
        host: "127.0.0.1"
        port: 9878
        auto_connect: false
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .config import PROJECT_ROOT

logger = logging.getLogger(__name__)

_ENGINES_LOCAL_PATH = PROJECT_ROOT / "engines.local.yaml"

_DEFAULTS: dict[str, dict[str, Any]] = {
    "unity": {"host": "127.0.0.1", "port": 9877, "auto_connect": False},
    "unreal": {"host": "127.0.0.1", "port": 9878, "auto_connect": False},
    "godot": {"host": "127.0.0.1", "port": 9879, "auto_connect": False},
}


def load_bridge_config(
    path: Path | None = None,
) -> dict[str, dict[str, Any]]:
    """Load bridge settings from *path* (defaults to ``engines.local.yaml``).

    Returns a dict keyed by engine name (lowercase), e.g.
    ``{"unity": {"host": "127.0.0.1", "port": 9877, "auto_connect": True}}``.

    Missing engines get default values.  If the file does not exist, all
    defaults are returned with ``auto_connect: False``.
    """
    file_path = path or _ENGINES_LOCAL_PATH
    result: dict[str, dict[str, Any]] = {}

    # Start with defaults
    for engine, defaults in _DEFAULTS.items():
        result[engine] = dict(defaults)

    if not file_path.exists():
        return result

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
    except Exception as exc:
        logger.warning("Failed to read bridge config from %s: %s", file_path, exc)
        return result

    if not raw or "bridges" not in raw:
        return result

    bridges = raw["bridges"]
    if not isinstance(bridges, dict):
        return result

    for engine, settings in bridges.items():
        engine = str(engine).strip().lower()
        if not isinstance(settings, dict):
            continue
        if engine not in result:
            result[engine] = {"host": "127.0.0.1", "port": 0, "auto_connect": False}
        result[engine].update(settings)

    return result
