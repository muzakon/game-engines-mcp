#!/usr/bin/env python3
"""Run the game-engine docs MCP server."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the src package is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from unity_mcp.server import main

if __name__ == "__main__":
    main()
