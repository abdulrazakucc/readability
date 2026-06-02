#!/usr/bin/env python3
"""Run the six readability formulas on every cleaned original page.

Output: data/scores/originals.csv keyed by page_id.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import CLEANED_DIR, MANIFEST_PATH, SCORES_DIR, ensure_dirs  # noqa: E402
from src.readability import score  # noqa: E402

log = logging.getLogger("score-originals")

OUT = SCORES_DIR / "originals.csv"

COLUMNS = [
    "page_id", "procedure", "site",
    "fkre", "fkgl", "gfi", "smog", "cli", "ari",
    "word_count", "sentence_count", "avg_words_per_sentence", "avg_syllables_per_word",
    "scorer_version",
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--included-only", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()

    rows = []
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))

    for row in manifest:
        if args.included_only and row.get("include", "").upper() != "Y":
            continue
        pid = row["page_id"]
        cleaned_path = CLEANED_DIR / f"{pid}.txt"
        if not cleaned_path.exists():
            log.warning("no cleaned text for %s — skipping", pid)
            continue
        text = cleaned_path.read_text(encoding="utf-8")
        s = score(text)
        rows.append({
            "page_id": pid,
            "procedure": row.get("procedure", ""),
            "site": row.get("site", ""),
            **{k: getattr(s, k) for k in [
                "fkre", "fkgl", "gfi", "smog", "cli", "ari",
                "word_count", "sentence_count", "avg_words_per_sentence", "avg_syllables_per_word",
                "scorer_version",
            ]}
        })
        log.info("scored %s fkgl=%.2f gfi=%.2f", pid, s.fkgl, s.gfi)

    with OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    log.info("wrote %d rows to %s", len(rows), OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
