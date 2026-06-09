#!/usr/bin/env python3
"""Aim 3 SECONDARY analysis: automated LLM-as-judge accuracy assessment.

A panel of three LLM judges scores every rewrite against its original on the
three locked rubric dimensions (docs/accuracy_scoring_rubric.md), blinded to the
producing model. This is a screening signal, NOT the pre-registered human
subspecialist review. Outputs are written under clearly-labeled `*_llm_*` names.

Usage:
  scripts/09_llm_accuracy.py --only-judge claude     # run one judge (parallelizable)
  scripts/09_llm_accuracy.py --aggregate             # merge cached judgments -> CSVs
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import CLEANED_DIR, CONFIG_DIR, MANIFEST_PATH, REWRITES_DIR, SCORES_DIR, ensure_dirs  # noqa: E402
from src.llm_judge import build_judges, score_one, _DIMS  # noqa: E402

log = logging.getLogger("llm-accuracy")

CACHE_DIR = SCORES_DIR / "judge_cache"
RAW_OUT = SCORES_DIR / "accuracy_llm_raw.csv"        # one row per (page, model, judge)
CONSENSUS_OUT = SCORES_DIR / "accuracy_llm.csv"      # one row per (page, model): mean across judges


def _rewrite_pairs():
    """Yield (page_id, model_id, original_text, rewrite_text) for every scorable rewrite."""
    with MANIFEST_PATH.open(encoding="utf-8") as f:
        included = {r["page_id"] for r in csv.DictReader(f) if r.get("include", "").upper() == "Y"}
    for rf in sorted(REWRITES_DIR.glob("*.txt")):  # quarantined files end in .excluded_* and are skipped
        page_id, _, model_id = rf.stem.rpartition("__")
        if page_id not in included:
            continue
        orig = (CLEANED_DIR / f"{page_id}.txt")
        if not orig.exists():
            continue
        yield page_id, model_id, orig.read_text(encoding="utf-8"), rf.read_text(encoding="utf-8")


def run_judges(only_judge: str | None, force: bool) -> int:
    with open(CONFIG_DIR / "models.yaml", encoding="utf-8") as f:
        specs = yaml.safe_load(f)["models"]
    judges = build_judges(specs)
    if only_judge:
        if only_judge not in judges:
            log.error("no judge %s in models.yaml", only_judge)
            return 2
        judges = {only_judge: judges[only_judge]}

    pairs = list(_rewrite_pairs())
    log.info("scoring %d rewrites with judges %s", len(pairs), list(judges))
    done = err = 0
    for jid, judge in judges.items():
        for page_id, model_id, original, rewrite in pairs:
            try:
                score_one(judge, jid, page_id, model_id, original, rewrite, CACHE_DIR, force=force)
                done += 1
                if done % 10 == 0:
                    log.info("  %d judgments cached", done)
            except Exception as exc:
                err += 1
                log.exception("judge %s failed on %s__%s: %s", jid, page_id, model_id, exc)
    log.info("judging complete: %d cached, %d errors", done, err)
    return 0


def aggregate() -> int:
    records = [json.loads(p.read_text()) for p in sorted(CACHE_DIR.glob("*.json"))]
    if not records:
        log.error("no cached judgments in %s", CACHE_DIR)
        return 2

    # Raw: one row per (page, model, judge)
    fields = ["page_id", "model_id", "judge_id", *_DIMS, "note", "flagged_claims"]
    with RAW_OUT.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in records:
            row = {k: r.get(k) for k in fields}
            row["flagged_claims"] = " | ".join(r.get("flagged_claims", []) or [])
            w.writerow(row)
    log.info("wrote %d raw judgments to %s", len(records), RAW_OUT)

    # Consensus: mean across judges per (page, model)
    import pandas as pd

    df = pd.DataFrame(records)
    cons = (
        df.groupby(["page_id", "model_id"])[list(_DIMS)]
        .mean()
        .round(3)
        .reset_index()
    )
    cons["n_judges"] = df.groupby(["page_id", "model_id"]).size().values
    cons.to_csv(CONSENSUS_OUT, index=False)
    log.info("wrote %d consensus rows to %s", len(cons), CONSENSUS_OUT)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only-judge", default=None, help="claude/openai/gemini")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--aggregate", action="store_true", help="merge cached judgments into CSVs")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()

    if args.aggregate:
        return aggregate()
    return run_judges(args.only_judge, args.force)


if __name__ == "__main__":
    sys.exit(main())
