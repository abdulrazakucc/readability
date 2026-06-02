"""Project paths, config loader, and constants.

Treat this module as the single source of truth for where files live and which
config a script is running under. Importing modules should never hard-code paths.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[1]

# --- Filesystem layout -------------------------------------------------------

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
CLEANED_DIR = DATA_DIR / "cleaned"
REWRITES_DIR = DATA_DIR / "rewrites"
SCORES_DIR = DATA_DIR / "scores"
REVIEW_DIR = DATA_DIR / "review"

CONFIG_DIR = REPO_ROOT / "config"
PROMPTS_DIR = REPO_ROOT / "prompts"
REPORTS_DIR = REPO_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
LITERATURE_DIR = REPO_ROOT / "literature"

MANIFEST_PATH = DATA_DIR / "manifest.csv"

ALL_DIRS = [
    DATA_DIR,
    RAW_DIR,
    CLEANED_DIR,
    REWRITES_DIR,
    SCORES_DIR,
    REVIEW_DIR,
    CONFIG_DIR,
    PROMPTS_DIR,
    REPORTS_DIR,
    FIGURES_DIR,
]


def ensure_dirs() -> None:
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)


# --- Procedures (locked) -----------------------------------------------------

PROCEDURES = ("tavr", "cta", "laao")
PROCEDURE_LABELS = {
    "tavr": "Pre-TAVR cardiac CT",
    "cta": "Coronary CTA",
    "laao": "LAAO / Watchman CT",
}


# --- Config loader -----------------------------------------------------------

@dataclass(frozen=True)
class ProjectConfig:
    raw: dict[str, Any]
    path: Path
    sha256: str

    def get(self, *keys: str, default: Any = None) -> Any:
        node: Any = self.raw
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return default
            node = node[k]
        return node


def load_config(path: str | Path | None = None) -> ProjectConfig:
    p = Path(path) if path else CONFIG_DIR / "default.yaml"
    with p.open("rb") as f:
        body = f.read()
    sha = hashlib.sha256(body).hexdigest()
    raw = yaml.safe_load(body) or {}
    return ProjectConfig(raw=raw, path=p.resolve(), sha256=sha)


# --- API keys ----------------------------------------------------------------

def get_api_key(provider: str) -> str | None:
    env_map = {
        "anthropic": "ANTHROPIC_API_KEY",
        "openai": "OPENAI_API_KEY",
        "google": "GOOGLE_API_KEY",
    }
    return os.environ.get(env_map.get(provider, ""))
