#!/usr/bin/env python3
"""Run the pre-registered statistical analyses for Aims 1, 2, and 3.

Per docs/statistical_analysis_plan.md — this script is LOCKED at Phase-5 start.
Any deviation must be logged in docs/stats_deviations.md.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import REPORTS_DIR, SCORES_DIR, ensure_dirs  # noqa: E402
from src.stats import (  # noqa: E402
    SCORE_COLS,
    aim1_across_groups,
    aim2_across_models,
    aim2_paired_per_model,
    aim3_clinical_model_comparison,
    aim3_tradeoff_correlations,
    describe_by,
    fraction_meeting_benchmark,
)

log = logging.getLogger("stats")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--originals", default=str(SCORES_DIR / "originals.csv"))
    parser.add_argument("--rewrites", default=str(SCORES_DIR / "rewrites.csv"))
    parser.add_argument("--deltas", default=str(SCORES_DIR / "deltas.csv"))
    parser.add_argument("--accuracy", default=str(SCORES_DIR / "accuracy.csv"))
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()

    originals = pd.read_csv(args.originals) if Path(args.originals).exists() else None
    rewrites = pd.read_csv(args.rewrites) if Path(args.rewrites).exists() else None
    deltas = pd.read_csv(args.deltas) if Path(args.deltas).exists() else None
    accuracy = pd.read_csv(args.accuracy) if Path(args.accuracy).exists() else None

    # --- Aim 1 ---
    if originals is not None and len(originals):
        log.info("Aim 1: descriptive + inferential on originals (n=%d)", len(originals))
        desc_overall = pd.DataFrame([
            {
                "score": col,
                "n": originals[col].notna().sum(),
                "mean": originals[col].mean(),
                "sd": originals[col].std(ddof=1),
                "median": originals[col].median(),
            }
            for col in SCORE_COLS
        ])
        desc_overall.to_csv(REPORTS_DIR / "aim1_descriptives_overall.csv", index=False)

        describe_by(originals, "site").to_csv(REPORTS_DIR / "aim1_descriptives_by_site.csv", index=False)
        describe_by(originals, "procedure").to_csv(REPORTS_DIR / "aim1_descriptives_by_procedure.csv", index=False)

        aim1_across_groups(originals, "site").to_csv(REPORTS_DIR / "aim1_inference_by_site.csv", index=False)
        aim1_across_groups(originals, "procedure").to_csv(REPORTS_DIR / "aim1_inference_by_procedure.csv", index=False)

        bench = fraction_meeting_benchmark(originals)
        pd.DataFrame([bench]).to_csv(REPORTS_DIR / "aim1_benchmark_meeting.csv", index=False)
        log.info("Aim 1 benchmark: %d/%d pages meet FKGL <= 6", bench["meeting"], bench["n"])

    # --- Aim 2 ---
    if originals is not None and rewrites is not None and len(rewrites):
        log.info("Aim 2: paired tests originals vs rewrites")
        paired = aim2_paired_per_model(originals, rewrites)
        paired.to_csv(REPORTS_DIR / "aim2_paired_tests.csv", index=False)

        across = aim2_across_models(rewrites)
        across.to_csv(REPORTS_DIR / "aim2_across_models.csv", index=False)

    # --- Aim 3 ---
    if deltas is not None and accuracy is not None and len(accuracy):
        log.info("Aim 3: trade-off correlations + model comparison on clinical scores")
        tradeoff = aim3_tradeoff_correlations(deltas, accuracy, primary_score="fkgl")
        tradeoff.to_csv(REPORTS_DIR / "aim3_tradeoff_correlations.csv", index=False)

        clin_desc = (
            accuracy
            .groupby("model_id")[["accuracy_1_5", "completeness_1_5", "added_errors_1_5"]]
            .agg(["mean", "std", "count"])
        )
        clin_desc.to_csv(REPORTS_DIR / "aim3_clinical_descriptives.csv")

        model_comp = aim3_clinical_model_comparison(accuracy)
        model_comp.to_csv(REPORTS_DIR / "aim3_model_comparison.csv", index=False)

    log.info("statistics complete — outputs in %s", REPORTS_DIR)
    return 0


if __name__ == "__main__":
    sys.exit(main())
