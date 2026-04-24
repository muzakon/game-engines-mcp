"""Unity editor bridge -- TCP client for the GameEngineMCP Unity plugin."""

from __future__ import annotations

from .base import EditorBridge


class UnityBridge(EditorBridge):
    """Bridge to a running Unity Editor via the GameEngineMCP TCP plugin.

    The Unity plugin listens on a configurable port (default 9877) and
    speaks the shared JSON wire protocol defined in :mod:`protocol`.

    No engine-specific overrides are needed: the base class handles
    the full command set over TCP.
    """

    engine: str = "unity"
