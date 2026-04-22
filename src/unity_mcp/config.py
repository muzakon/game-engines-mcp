"""Project configuration and path constants."""

from pathlib import Path

# Project root (where pyproject.toml lives)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Source manifests and generated data
DOCSETS_MANIFEST_PATH = PROJECT_ROOT / "docsets.json"
DATA_DIR = PROJECT_ROOT / "data"

# Legacy/default Unity paths kept for compatibility and sensible defaults.
DOCS_ROOT = PROJECT_ROOT / "docs" / "unity" / "current" / "reference"
DB_PATH = DATA_DIR / "unity" / "current" / "reference.db"

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

# Default routing for backwards-compatible Unity tools
DEFAULT_ENGINE = "unity"
DEFAULT_UNITY_VERSION = "current"
DEFAULT_UNITY_DOCSET = "reference"

# Schema version written to each SQLite metadata table
DB_SCHEMA_VERSION = "2"
