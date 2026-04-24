"""Import guard for Unreal's editor-only Python module."""

from __future__ import annotations

try:
    import unreal
except ImportError as exc:
    raise ImportError(
        "The 'unreal' module is only available inside the Unreal Editor. "
        "Enable the Python Editor Script Plugin and restart the editor."
    ) from exc

__all__ = ["unreal"]
