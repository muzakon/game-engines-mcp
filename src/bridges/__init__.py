"""Live editor bridge infrastructure.

Provides TCP-based communication with running game engine editors
(Unity, Unreal, Godot) through a unified JSON wire protocol.
"""

from .base import EditorBridge
from .protocol import encode_command, decode_response, McpRequest, McpResponse
from .registry import BridgeRegistry

__all__ = [
    "EditorBridge",
    "BridgeRegistry",
    "encode_command",
    "decode_response",
    "McpRequest",
    "McpResponse",
]
