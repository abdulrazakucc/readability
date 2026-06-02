#!/usr/bin/env python3
"""Build the blinded review packet for Aim 3 clinical scoring.

Outputs:
  data/review/review_packet.csv  (hand to the reviewer)
  data/review/blind_key.csv      (keep — used to unblind later)
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import CLEANED_DIR, CONFIG_DIR, MANIFEST_PATH, REVIEW_DIR, REWRITES_DIR, ensure_dirs, load_config  # noqa: E402
from src.scoring import build_packet  # noqa: E402

log = logging.getLogger("review-packet")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=str(CONFIG_DIR / "models.yaml"))
    parser.add_argument("--config", default=None)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    cfg = load_config(args.config)
    seed = int(cfg.get("random_seed", default=42))

    with MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest = list(csv.DictReader(f))
    page_ids = [r["page_id"] for r in manifest if r.get("include", "").upper() == "Y"]

    with open(args.models, "r", encoding="utf-8") as f:
        model_ids = [m["id"] for m in yaml.safe_load(f)["models"]]

    packet, key, entries = build_packet(
        page_ids=page_ids,
        model_ids=model_ids,
        cleaned_dir=CLEANED_DIR,
        rewrites_dir=REWRITES_DIR,
        out_dir=REVIEW_DIR,
        seed=seed,
    )
    log.info("built packet with %d entries", len(entries))
    log.info("packet: %s", packet)
    log.info("blind key (DO NOT SHARE): %s", key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
