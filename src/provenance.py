"""Provenance helpers: content hashing, git SHA, timestamps, JSON sidecars."""

from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git_sha(repo: str | Path | None = None) -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(repo) if repo else None,
            check=True,
            capture_output=True,
            text=True,
        )
        sha = out.stdout.strip()
        dirty = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(repo) if repo else None,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def write_provenance(path: str | Path, data: dict[str, Any]) -> None:
    """Write a provenance sidecar as JSON. Always overwrites — provenance must be current."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")


def base_provenance(config_sha: str | None = None) -> dict[str, Any]:
    return {
        "generated_at_utc": utc_now_iso(),
        "git_sha": git_sha(),
        "config_sha256": config_sha,
    }
