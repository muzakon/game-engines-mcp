"""Download pre-built documentation indexes from GitHub Releases."""

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

GITHUB_RELEASE_URL = (
    "https://github.com/{owner}/{repo}/releases/download/{tag}/{asset}"
)


@dataclass(frozen=True)
class ReleaseConfig:
    owner: str
    repo: str


@dataclass(frozen=True)
class EngineEntry:
    engine: str
    version: str
    docsets: list[str]


@dataclass
class AppConfig:
    release: ReleaseConfig
    engines: list[EngineEntry]


def load_config(config_path: Path | None = None) -> AppConfig:
    path = config_path or CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    rel = raw.get("release", {})
    release_cfg = ReleaseConfig(
        owner=rel.get("owner", ""),
        repo=rel.get("repo", "game-engine-mcp"),
    )
    engines: list[EngineEntry] = []
    for entry in raw.get("engines", []):
        engines.append(EngineEntry(
            engine=entry["engine"],
            version=str(entry["version"]),
            docsets=list(entry.get("docsets", ["reference"])),
        ))
    return AppConfig(release=release_cfg, engines=engines)


def _release_tag(engine: str, version: str, docset: str) -> str:
    return f"{engine}-{version}-{docset}"


def _db_path(engine: str, version: str, docset: str) -> Path:
    return DATA_DIR / engine / version / f"{docset}.db"


def _download_url(release: ReleaseConfig, tag: str, asset: str) -> str:
    return GITHUB_RELEASE_URL.format(
        owner=release.owner,
        repo=release.repo,
        tag=tag,
        asset=asset,
    )


def _download_and_decompress(url: str, dest: Path) -> None:
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

        logger.info("Decompressed database to %s (%.1f MB)", dest, dest.stat().st_size / 1e6)
    except (urllib.error.HTTPError, urllib.error.URLError) as exc:
        logger.error("Failed to download %s: %s", url, exc)
        raise
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def ensure_databases(
    config_path: Path | None = None,
    force: bool = False,
) -> list[Path]:
    """Download all configured databases that don't yet exist locally.

    Returns list of database paths that are ready to use.
    """
    config = load_config(config_path)
    ready: list[Path] = []

    for entry in config.engines:
        for docset in entry.docsets:
            db = _db_path(entry.engine, entry.version, docset)

            if db.exists() and not force:
                logger.info("Database already exists: %s", db)
                ready.append(db)
                continue

            tag = _release_tag(entry.engine, entry.version, docset)
            asset = f"{docset}.db.gz"
            url = _download_url(config.release, tag, asset)

            try:
                _download_and_decompress(url, db)
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
