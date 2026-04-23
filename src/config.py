"""Project configuration and path constants."""

from pathlib import Path


def _find_project_root() -> Path:
    """Find the project root by walking up from this file and falling back to cwd.

    When installed as a package (e.g. in Docker via ``uv sync``), __file__ lives
    inside site-packages so parent-based resolution breaks.  We detect that by
    checking for ``pyproject.toml`` and fall back to cwd when needed.
    """
    candidate = Path(__file__).resolve().parents[1]
    if (candidate / "pyproject.toml").is_file():
        return candidate
    # Fallback: assume cwd is the project root (true in Docker with WORKDIR /app)
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").is_file():
        return cwd
    # Last resort: use the original heuristic
    return Path(__file__).resolve().parents[2]


# Project root (where pyproject.toml lives)
PROJECT_ROOT = _find_project_root()

# Source manifests and generated data
DOCSETS_MANIFEST_PATH = PROJECT_ROOT / "docsets.json"
DATA_DIR = PROJECT_ROOT / "data"

# Supported HTML extensions
HTML_EXTENSIONS = {".html", ".htm"}

# Common file names to ignore across docsets
SKIP_FILENAMES = {"30_search.html", "docdata.html"}

# Unity-specific asset folders to skip
UNITY_SKIP_DIRS = {"StaticFiles", "StaticFilesManual", "uploads"}

# Max content length to store per page (characters)
MAX_CONTENT_LENGTH = 100_000

# Default search result limit
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50

# Schema version written to each SQLite metadata table
DB_SCHEMA_VERSION = "2"
