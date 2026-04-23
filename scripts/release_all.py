#!/usr/bin/env python3
"""Upload all configured docset databases to GitHub Releases.

Uses the GitHub REST API directly (via curl) so the `gh` CLI is not required.
Set the GITHUB_TOKEN environment variable to a personal access token with
repo-level write access before running.
"""

from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import DATA_DIR
from src.downloader import load_config


def _curl(*args: str) -> tuple[int, str, str]:
    """Run curl and return (http_status_code, stdout, stderr)."""
    r = subprocess.run(
        ["curl", "-s", "-o", "-", "-w", "\n%{http_code}", *args],
        capture_output=True,
        text=True,
    )
    output = r.stdout
    # Last line is the HTTP status code injected by -w
    parts = output.rsplit("\n", 1)
    body = parts[0]
    status_code = (
        int(parts[1].strip()) if len(parts) == 2 and parts[1].strip().isdigit() else 0
    )
    return status_code, body, r.stderr


def _github_token() -> str:
    token = os.environ.get("GITHUB_TOKEN", "")
    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is not set.")
        print(
            "       Generate one at https://github.com/settings/tokens with 'repo' scope."
        )
        sys.exit(1)
    return token


def _api_error(action: str, status: int, body: str) -> str:
    try:
        msg = json.loads(body).get("message", body)
    except (json.JSONDecodeError, AttributeError):
        msg = body[:300]
    return f"Failed to {action} (HTTP {status}): {msg}"


def _create_or_get_release(
    token: str,
    owner: str,
    repo: str,
    tag: str,
    body: str,
) -> str:
    """Return the release ID, creating the release if it doesn't exist."""

    headers = [
        "-H",
        f"Authorization: token {token}",
        "-H",
        "Accept: application/vnd.github+json",
    ]

    # Try to fetch existing release
    api = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    status, resp, _ = _curl(*headers, api)
    if status == 200:
        data = json.loads(resp)
        release_id = data["id"]
        print(f"  Release {tag} already exists (id={release_id})")
        return str(release_id)

    # Create a new release
    payload = json.dumps(
        {
            "tag_name": tag,
            "name": tag,
            "body": body,
            "draft": False,
            "prerelease": False,
        }
    )
    api = f"https://api.github.com/repos/{owner}/{repo}/releases"
    status, resp, _ = _curl(*headers, "-X", "POST", "-d", payload, api)
    if status != 201:
        raise RuntimeError(_api_error(f"create release {tag}", status, resp))
    data = json.loads(resp)
    release_id = data["id"]
    print(f"  Created release {tag} (id={release_id})")
    return str(release_id)


def _upload_asset(
    token: str,
    owner: str,
    repo: str,
    release_id: str,
    asset_path: Path,
) -> None:
    upload_url = (
        f"https://uploads.github.com/repos/{owner}/{repo}/releases/"
        f"{release_id}/assets?name={asset_path.name}"
    )
    status, resp, _ = _curl(
        "-H",
        f"Authorization: token {token}",
        "-H",
        "Content-Type: application/gzip",
        "-X",
        "POST",
        "--data-binary",
        f"@{asset_path}",
        upload_url,
    )
    if status not in (200, 201):
        raise RuntimeError(_api_error(f"upload {asset_path.name}", status, resp))


def main() -> None:
    config = load_config()
    token = _github_token()
    owner = config.release.owner
    repo = config.release.repo

    for entry in config.engines:
        for docset in entry.docsets:
            db_path = DATA_DIR / entry.engine / entry.version / f"{docset}.db"
            tag = f"{entry.engine}-{entry.version}-{docset}"

            if not db_path.exists():
                print(f"SKIP  {tag}: database not found at {db_path}")
                continue

            gz_path = db_path.with_suffix(".db.gz")
            print(f"Compressing {db_path} -> {gz_path}")
            with open(db_path, "rb") as f_in:
                with gzip.open(gz_path, "wb") as f_out:
                    f_out.writelines(f_in)

            size_mb = gz_path.stat().st_size / 1e6
            print(f"Uploading {tag} ({size_mb:.1f} MB compressed) ...")

            try:
                release_id = _create_or_get_release(
                    token,
                    owner,
                    repo,
                    tag,
                    body=f"Pre-built index for {entry.engine} {entry.version} {docset}",
                )
                _upload_asset(token, owner, repo, release_id, gz_path)
                print(f"  OK   {tag}")
            except RuntimeError as exc:
                print(f"  FAIL {tag}: {exc}")
            finally:
                gz_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
