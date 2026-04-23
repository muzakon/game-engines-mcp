"""Project paths and tuning constants.

Everything in this module is a plain constant so other modules can do a
simple ``from .config import PROJECT_ROOT`` without worrying about
import-order side-effects.
"""

from pathlib import Path


def _find_project_root() -> Path:
    """Locate the project root (directory containing ``pyproject.toml``).

    Resolution order:
      1. Parent of this file's directory (works in normal ``src/`` layouts).
      2. Current working directory (works inside Docker containers).
      3. Two levels up from this file (legacy fallback).
    """
    candidate = Path(__file__).resolve().parents[1]
    if (candidate / "pyproject.toml").is_file():
        return candidate
    cwd = Path.cwd()
    if (cwd / "pyproject.toml").is_file():
        return cwd
    return Path(__file__).resolve().parents[2]


# -- Paths -----------------------------------------------------------------

PROJECT_ROOT: Path = _find_project_root()
"""Repository / package root (contains ``pyproject.toml``)."""

DOCSETS_MANIFEST_PATH: Path = PROJECT_ROOT / "docsets.json"
"""Default JSON manifest shipped with the repo."""

DATA_DIR: Path = PROJECT_ROOT / "data"
"""Directory where built SQLite databases are stored."""

# -- File-discovery constants -----------------------------------------------

HTML_EXTENSIONS: frozenset[str] = frozenset({".html", ".htm"})
"""File extensions considered indexable HTML."""

SKIP_FILENAMES: frozenset[str] = frozenset({"30_search.html", "docdata.html"})
"""Filenames to skip regardless of extension."""

UNITY_SKIP_DIRS: frozenset[str] = frozenset({"StaticFiles", "StaticFilesManual", "uploads"})
"""Unity-specific directories to skip during HTML discovery."""

# -- Limits -----------------------------------------------------------------

MAX_CONTENT_LENGTH: int = 100_000
"""Maximum characters of page content stored per record."""

DEFAULT_SEARCH_LIMIT: int = 10
"""Default number of search results returned."""

MAX_SEARCH_LIMIT: int = 50
"""Hard upper-bound on search result count."""

# -- Vector search ---------------------------------------------------------

VECTOR_DIM: int = 384
"""Embedding dimension (all-MiniLM-L6-v2 produces 384-dim vectors)."""

VECTOR_MODEL_NAME: str = "all-MiniLM-L6-v2"
"""Sentence-transformers model used for embedding generation."""

VECTOR_DB_DIR: Path = DATA_DIR / "vectors"
"""Directory where LanceDB vector stores are saved."""

EMBEDDING_BATCH_SIZE: int = 64
"""Number of records to embed in a single batch."""

# -- Schema -----------------------------------------------------------------

DB_SCHEMA_VERSION: str = "3"
"""Schema version string written into every SQLite ``metadata`` table."""
