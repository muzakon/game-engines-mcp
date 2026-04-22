"""CLI smoke tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_build_index_list_docsets_smoke() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/build_index.py", "--list-docsets"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "godot:4.6:reference" in result.stdout
