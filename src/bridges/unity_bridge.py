"""Unity editor bridge -- TCP client for the GameEngineMCP Unity plugin.

Unity-specific commands should be added here as methods on
:class:`UnityBridge`.  The shared base commands (play, stop, scene
hierarchy, object CRUD, etc.) are inherited from :class:`EditorBridge`.
"""

from __future__ import annotations

from .base import EditorBridge


class UnityBridge(EditorBridge):
    """Bridge to a running Unity Editor via the GameEngineMCP TCP plugin.

    The Unity plugin listens on a configurable port (default 9877) and
    speaks the shared JSON wire protocol defined in :mod:`protocol`.

    Add Unity-specific command methods here as the Unity plugin grows.
    """

    engine: str = "unity"
