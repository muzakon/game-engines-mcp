"""Download pre-built documentation indexes from GitHub Releases.

The download configuration is split across two files:

* ``config.yaml`` (tracked) – contains the ``release`` section (owner/repo).
* ``engines.local.yaml`` (gitignored) – contains the user's ``engines`` list.

Usage::

    from src.downloader import DatabaseDownloader

    downloader = DatabaseDownloader()
    downloader.ensure_all()
"""

from __future__ import annotations

import gzip
import logging
import shutil
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path

import yaml

from .config import DATA_DIR, PROJECT_ROOT

logger = logging.getLogger(__name__)

CONFIG_PATH = PROJECT_ROOT / "config.yaml"
ENGINES_PATH = PROJECT_ROOT / "engines.local.yaml"

GITHUB_RELEASE_URL = "https://github.com/{owner}/{repo}/releases/download/{tag}/{asset}"


# ---------------------------------------------------------------------------
# Configuration dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ReleaseConfig:
    """GitHub owner/repo that hosts release assets."""

    owner: str
    repo: str


@dataclass(frozen=True)
class EngineEntry:
    """One engine entry from ``engines.local.yaml``."""

    engine: str
    version: str
    docsets: list[str]


@dataclass
class AppConfig:
    """Merged configuration used by :class:`DatabaseDownloader`."""

    release: ReleaseConfig
    engines: list[EngineEntry]


# ---------------------------------------------------------------------------
# Downloader
# ---------------------------------------------------------------------------


class DatabaseDownloader:
    """Download and decompress ``.db.gz`` assets from GitHub Releases.

    Example::

        dl = DatabaseDownloader()
        ready = dl.ensure_all()          # skip existing, download missing
        ready = dl.ensure_all(force=True)  # re-download everything
    """

    def __init__(
        self,
        config_path: Path | None = None,
        engines_path: Path | None = None,
    ) -> None:
        self._config_path = config_path or CONFIG_PATH
        self._engines_path = engines_path or ENGINES_PATH
        self._config: AppConfig | None = None

    # -- public API ----------------------------------------------------------

    def ensure_all(self, *, force: bool = False) -> list[Path]:
        """Download every configured database that is not yet on disk.

        Args:
            force: When *True*, re-download even if the ``.db`` already exists.

        Returns:
            List of database paths that are ready to use.
        """
        config = self._load_config()
        ready: list[Path] = []

        for entry in config.engines:
            for docset in entry.docsets:
                db = self._db_path(entry.engine, entry.version, docset)

                if db.exists() and not force:
                    logger.info("Database already exists: %s", db)
                    ready.append(db)
                    continue

                tag = self._release_tag(entry.engine, entry.version, docset)
                asset = f"{docset}.db.gz"
                url = self._download_url(config.release, tag, asset)

                try:
                    self._download_and_decompress(url, db)
                    ready.append(db)
                except Exception as exc:
                    logger.warning(
                        "Could not download %s/%s/%s: %s. "
                        "You may need to build the index locally with: make index",
                        entry.engine,
                        entry.version,
                        docset,
                        exc,
                    )

        return ready

    # -- config loading ------------------------------------------------------

    def _load_config(self) -> AppConfig:
        """Parse and cache ``config.yaml`` + ``engines.local.yaml``."""
        if self._config is not None:
            return self._config

        if not self._config_path.exists():
            raise FileNotFoundError(
                f"Configuration file not found: {self._config_path}"
            )

        release_cfg = self._load_release_config(self._config_path)
        engines = self._load_engines(self._engines_path)
        self._config = AppConfig(release=release_cfg, engines=engines)
        return self._config

    @staticmethod
    def _load_release_config(path: Path) -> ReleaseConfig:
        """Read the ``release`` section from *path*."""
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        rel = raw.get("release", {})
        return ReleaseConfig(
            owner=rel.get("owner", ""),
            repo=rel.get("repo", "game-engine-mcp"),
        )

    @staticmethod
    def _load_engines(path: Path) -> list[EngineEntry]:
        """Read the ``engines`` list from *path* (may not exist)."""
        if not path.exists():
            return []
        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        return [
            EngineEntry(
                engine=entry["engine"],
                version=str(entry["version"]),
                docsets=list(entry.get("docsets", ["reference"])),
            )
            for entry in raw.get("engines", [])
        ]

    # -- download helpers ----------------------------------------------------

    @staticmethod
    def _release_tag(engine: str, version: str, docset: str) -> str:
        """Build the GitHub release tag for a given engine/version/docset."""
        return f"{engine}-{version}-{docset}"

    @staticmethod
    def _db_path(engine: str, version: str, docset: str) -> Path:
        """Default filesystem path for a docset database."""
        return DATA_DIR / engine / version / f"{docset}.db"

    @staticmethod
    def _download_url(release: ReleaseConfig, tag: str, asset: str) -> str:
        """Build the full GitHub release download URL."""
        return GITHUB_RELEASE_URL.format(
            owner=release.owner,
            repo=release.repo,
            tag=tag,
            asset=asset,
        )

    @staticmethod
    def _download_and_decompress(url: str, dest: Path) -> None:
        """Download a ``.db.gz`` asset and decompress it to *dest*."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = dest.with_suffix(".db.gz.tmp")

        try:
            logger.info("Downloading %s -> %s", url, dest)
            req = urllib.request.Request(url, headers={"User-Agent": "game-engine-mcp"})
            with urllib.request.urlopen(req, timeout=300) as resp:
                with open(tmp_path, "wb") as f:
                    shutil.copyfileobj(resp, f)

            with gzip.open(tmp_path, "rb") as gz:
                with open(dest, "wb") as out:
                    shutil.copyfileobj(gz, out)

            logger.info(
                "Decompressed database to %s (%.1f MB)",
                dest,
                dest.stat().st_size / 1e6,
            )
        except (urllib.error.HTTPError, urllib.error.URLError) as exc:
            logger.error("Failed to download %s: %s", url, exc)
            raise
        finally:
            if tmp_path.exists():
                tmp_path.unlink()


# ---------------------------------------------------------------------------
# Legacy function API (kept for backward compatibility)
# ---------------------------------------------------------------------------


def load_config(
    config_path: Path | None = None,
    engines_path: Path | None = None,
) -> AppConfig:
    """Load merged configuration.  Kept for scripts that only need config."""
    dl = DatabaseDownloader(config_path=config_path, engines_path=engines_path)
    return dl._load_config()


def ensure_databases(
    config_path: Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Download all configured databases that don't yet exist locally."""
    dl = DatabaseDownloader(config_path=config_path)
    return dl.ensure_all(force=force)
