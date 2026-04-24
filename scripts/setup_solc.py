"""
Install a pinned Solidity compiler into solc-select's artifact layout.

This is a practical fallback for environments where `solc-select install`
fails because the upstream artifact endpoint rejects urllib's default client.

Usage:
    python scripts/setup_solc.py
    python scripts/setup_solc.py 0.8.20
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from pathlib import Path

import requests

DEFAULT_VERSION = "0.8.20"
USER_AGENT = "BlockScope/1.0 (+https://github.com/harshilnayi/BlockScope)"
SOLIDITY_BASE = "https://binaries.soliditylang.org"
SOLC_SELECT_DIR = Path.home() / ".solc-select"
ARTIFACTS_DIR = SOLC_SELECT_DIR / "artifacts"

PLATFORM_MAP = {
    "Windows": "windows-amd64",
    "Linux": "linux-amd64",
    "Darwin": "macosx-amd64",
}


def get_platform_slug() -> str:
    system = platform.system()
    slug = PLATFORM_MAP.get(system)
    if slug is None:
        raise RuntimeError(f"Unsupported platform for this bootstrap script: {system}")
    return slug


def fetch_json(url: str) -> dict:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=120)
    response.raise_for_status()
    return response.json()


def download_bytes(url: str) -> bytes:
    response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=300)
    response.raise_for_status()
    return response.content


def install(version: str) -> Path:
    platform_slug = get_platform_slug()
    list_url = f"{SOLIDITY_BASE}/{platform_slug}/list.json"
    data = fetch_json(list_url)

    artifact_name = data["releases"].get(version)
    if artifact_name is None:
        raise RuntimeError(f"Solidity version {version} is not available for {platform_slug}")

    build = next(item for item in data["builds"] if item["path"] == artifact_name)
    artifact_url = f"{SOLIDITY_BASE}/{platform_slug}/{artifact_name}"
    expected_sha256 = build["sha256"].replace("0x", "")

    content = download_bytes(artifact_url)
    actual_sha256 = hashlib.sha256(content).hexdigest()
    if actual_sha256.lower() != expected_sha256.lower():
        raise RuntimeError(
            f"SHA256 mismatch for solc {version}: {actual_sha256} != {expected_sha256}"
        )

    artifact_dir = ARTIFACTS_DIR / f"solc-{version}"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = artifact_dir / f"solc-{version}"
    artifact_path.write_bytes(content)

    if platform.system() != "Windows":
        artifact_path.chmod(0o775)

    SOLC_SELECT_DIR.mkdir(parents=True, exist_ok=True)
    (SOLC_SELECT_DIR / "global-version").write_text(version, encoding="utf-8")
    return artifact_path


def main() -> int:
    version = sys.argv[1] if len(sys.argv) > 1 else os.getenv("SOLC_VERSION", DEFAULT_VERSION)
    artifact_path = install(version)
    print(f"Installed solc {version} at {artifact_path}")
    print(f"Activated solc {version} in {SOLC_SELECT_DIR / 'global-version'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
