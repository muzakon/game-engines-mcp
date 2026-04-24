"""Godot editor bridge -- re-exported from godot_commands for backward compat."""

from __future__ import annotations

# The concrete GodotBridge class now lives in godot_commands.py
# so that engine-specific commands are separated from the shared base.
from .godot_commands import GodotBridge  # noqa: F401

__all__ = ["GodotBridge"]
