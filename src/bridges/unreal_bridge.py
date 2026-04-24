"""Unreal Engine editor bridge -- TCP client for the GameEngineMCP UE plugin."""

from __future__ import annotations

from .base import EditorBridge


class UnrealBridge(EditorBridge):
    """Bridge to a running Unreal Editor via the GameEngineMCP TCP plugin.

    The UE plugin listens on a configurable port (default 9878) and
    speaks the shared JSON wire protocol.
    """

    engine: str = "unreal"
