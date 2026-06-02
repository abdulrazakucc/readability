#!/usr/bin/env python3
"""Clean every captured page (or just the included ones) into body-only text.

Reads `data/manifest.csv` and `data/raw/<page_id>.html`, writes
`data/cleaned/<page_id>.txt` and updates the manifest's cleaned_path and
word_count_cleaned columns.
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import CLEANED_DIR, MANIFEST_PATH, RAW_DIR, ensure_dirs  # noqa: E402
from src.clean import clean  # noqa: E402

log = logging.getLogger("clean")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--included-only", action="store_true",
                        help="Only clean pages with include=Y in the manifest")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()

    if not MANIFEST_PATH.exists():
        log.error("manifest not found at %s — run 01_capture_pages.py first", MANIFEST_PATH)
        return 2

    rows: list[dict] = []
    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        if args.included_only and row.get("include", "").upper() != "Y":
            continue
        pid = row["page_id"]
        raw_path = REPO_ROOT / row["raw_path"] if row.get("raw_path") else RAW_DIR / f"{pid}.html"
        if not raw_path.exists():
            log.warning("raw not found for %s at %s — skipping", pid, raw_path)
            continue

        cleaned_path = CLEANED_DIR / f"{pid}.txt"
        if cleaned_path.exists() and not args.force:
            log.info("%s already cleaned — skipping", pid)
            row["cleaned_path"] = str(cleaned_path.relative_to(REPO_ROOT))
            row.setdefault("word_count_cleaned", str(len(cleaned_path.read_text(encoding="utf-8").split())))
            continue

        raw_html = raw_path.read_bytes()
        result = clean(pid, raw_html, CLEANED_DIR)
        row["cleaned_path"] = str(result.cleaned_path.relative_to(REPO_ROOT))
        row["word_count_cleaned"] = str(result.word_count)
        log.info("cleaned %s (%d words)", pid, result.word_count)

    fieldnames = list(rows[0].keys()) if rows else []
    if fieldnames:
        with MANIFEST_PATH.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(rows)
        log.info("manifest updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
