#!/usr/bin/env python3
"""Score every AI rewrite with the six readability formulas, then compute deltas vs originals."""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import MANIFEST_PATH, REWRITES_DIR, SCORES_DIR, ensure_dirs  # noqa: E402
from src.readability import score  # noqa: E402

log = logging.getLogger("score-rewrites")

REWRITES_OUT = SCORES_DIR / "rewrites.csv"
DELTAS_OUT = SCORES_DIR / "deltas.csv"
ORIGINALS_PATH = SCORES_DIR / "originals.csv"

SCORE_COLS = ["fkre", "fkgl", "gfi", "smog", "cli", "ari"]
META_COLS = ["word_count", "sentence_count", "avg_words_per_sentence", "avg_syllables_per_word", "scorer_version"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()

    if not ORIGINALS_PATH.exists():
        log.error("originals.csv not found — run 03_score_originals.py first")
        return 2

    rows = []
    for rewrite_file in sorted(REWRITES_DIR.glob("*.txt")):
        stem = rewrite_file.stem  # "<page_id>__<model_id>"
        if "__" not in stem:
            continue
        page_id, _, model_id = stem.partition("__")
        # page_id itself contains "__" — re-parse: split rsplit on last "__"
        page_id, _, model_id = stem.rpartition("__")
        text = rewrite_file.read_text(encoding="utf-8")
        s = score(text)
        rows.append({
            "page_id": page_id,
            "model_id": model_id,
            **{k: getattr(s, k) for k in SCORE_COLS + META_COLS},
        })
        log.info("scored rewrite %s × %s fkgl=%.2f", page_id, model_id, s.fkgl)

    df = pd.DataFrame(rows)
    df.to_csv(REWRITES_OUT, index=False)
    log.info("wrote %d rewrite scores to %s", len(df), REWRITES_OUT)

    # Build deltas table
    orig = pd.read_csv(ORIGINALS_PATH)[["page_id"] + SCORE_COLS]
    merged = df.merge(orig, on="page_id", suffixes=("_rewrite", "_orig"))
    for col in SCORE_COLS:
        merged[f"{col}_delta"] = merged[f"{col}_rewrite"] - merged[f"{col}_orig"]
    delta_cols = ["page_id", "model_id"] + [f"{c}_delta" for c in SCORE_COLS] + [f"{c}_rewrite" for c in SCORE_COLS] + [f"{c}_orig" for c in SCORE_COLS]
    merged[delta_cols].to_csv(DELTAS_OUT, index=False)
    log.info("wrote %d delta rows to %s", len(merged), DELTAS_OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
