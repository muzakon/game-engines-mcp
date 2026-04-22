"""Project configuration and path constants."""

from pathlib import Path

# Project root (where pyproject.toml lives)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

# Documentation root
DOCS_ROOT = PROJECT_ROOT / "Documentation"

# Database location
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "unity_docs.db"

# HTML file extensions to index
HTML_EXTENSIONS = {".html", ".htm"}

# Directories under Documentation to skip (assets, images, etc.)
SKIP_DIRS = {"StaticFiles", "StaticFilesManual", "uploads"}

# Max content length to store per page (characters)
MAX_CONTENT_LENGTH = 100_000

# Default search result limit
DEFAULT_SEARCH_LIMIT = 10
MAX_SEARCH_LIMIT = 50
