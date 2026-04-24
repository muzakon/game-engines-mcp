"""Godot editor bridge -- TCP client for the GameEngineMCP Godot addon."""

from __future__ import annotations

from .base import EditorBridge


class GodotBridge(EditorBridge):
    """Bridge to a running Godot Editor via the GameEngineMCP TCP addon.

    The Godot addon listens on a configurable port (default 9879) and
    speaks the shared JSON wire protocol.
    """

    engine: str = "godot"
