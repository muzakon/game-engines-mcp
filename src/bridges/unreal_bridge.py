"""Unreal Engine editor bridge -- re-exported from unreal_commands for backward compat."""

from __future__ import annotations

# The concrete UnrealBridge class now lives in unreal_commands.py
# so that engine-specific commands are separated from the shared base.
from .unreal_commands import UnrealBridge  # noqa: F401

__all__ = ["UnrealBridge"]
