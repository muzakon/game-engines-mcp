"""Unreal Engine editor bridge -- TCP client for the GameEngineMCP UE plugin.

Unreal-specific commands should be added here as methods on
:class:`UnrealBridge`.  The shared base commands (play, stop, scene
hierarchy, object CRUD, etc.) are inherited from :class:`EditorBridge`.
"""

from __future__ import annotations

from .base import EditorBridge


class UnrealBridge(EditorBridge):
    """Bridge to a running Unreal Editor via the GameEngineMCP TCP plugin.

    The UE plugin listens on a configurable port (default 9878) and
    speaks the shared JSON wire protocol.

    Add Unreal-specific command methods here as the UE plugin grows.
    """

    engine: str = "unreal"
