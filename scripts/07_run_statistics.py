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
    clopper_pearson,
    describe_by,
    dunn_posthoc,
    fraction_meeting_benchmark,
    pairwise_posthoc_models,
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
                "iqr_low": originals[col].quantile(0.25),
                "iqr_high": originals[col].quantile(0.75),
            }
            for col in SCORE_COLS
        ])
        desc_overall.to_csv(REPORTS_DIR / "aim1_descriptives_overall.csv", index=False)

        describe_by(originals, "site").to_csv(REPORTS_DIR / "aim1_descriptives_by_site.csv", index=False)
        describe_by(originals, "procedure").to_csv(REPORTS_DIR / "aim1_descriptives_by_procedure.csv", index=False)

        aim1_across_groups(originals, "site").to_csv(REPORTS_DIR / "aim1_inference_by_site.csv", index=False)
        aim1_across_groups(originals, "procedure").to_csv(REPORTS_DIR / "aim1_inference_by_procedure.csv", index=False)

        # SAP requires post-hoc follow-up after a significant omnibus. FKRE and CLI
        # both show significant site-level differences that the manuscript does not
        # currently report.
        site_ph = []
        site_inf = aim1_across_groups(originals, "site")
        for _, r in site_inf.iterrows():
            if not (r["p"] < 0.05):
                continue
            groups = {g: sub[r["score"]].dropna().to_numpy()
                      for g, sub in originals.groupby("site")}
            groups = {k: v for k, v in groups.items() if len(v) >= 2}
            out = dunn_posthoc(groups)
            out.insert(0, "score", r["score"])
            site_ph.append(out)
        if site_ph:
            pd.concat(site_ph, ignore_index=True).to_csv(
                REPORTS_DIR / "aim1_posthoc_sites.csv", index=False)
            log.info("Aim 1: wrote site post-hoc for %d score(s)", len(site_ph))

        bench = fraction_meeting_benchmark(originals)
        # Exact binomial CI belongs in the report, not only in the manuscript prose.
        lo, hi = clopper_pearson(bench["meeting"], bench["n"])
        bench["ci_low"] = lo
        bench["ci_high"] = hi
        bench["ci_low_pct"] = 100 * lo
        bench["ci_high_pct"] = 100 * hi
        pd.DataFrame([bench]).to_csv(REPORTS_DIR / "aim1_benchmark_meeting.csv", index=False)
        log.info("Aim 1 benchmark: %d/%d pages meet FKGL <= 6", bench["meeting"], bench["n"])

    # --- Aim 2 ---
    if originals is not None and rewrites is not None and len(rewrites):
        log.info("Aim 2: paired tests originals vs rewrites")
        paired = aim2_paired_per_model(originals, rewrites)
        paired.to_csv(REPORTS_DIR / "aim2_paired_tests.csv", index=False)

        # Post-rewrite descriptives + benchmark counts, so every manuscript figure
        # of the form "22 of 26" traces to a generated report.
        desc_rows = []
        for mid, sub in rewrites.groupby("model_id"):
            row = {"model_id": mid, "n_rewrites": len(sub)}
            for col in SCORE_COLS:
                row[f"{col}_mean"] = sub[col].mean()
                row[f"{col}_sd"] = sub[col].std(ddof=1)
                row[f"{col}_median"] = sub[col].median()
                row[f"{col}_iqr_low"] = sub[col].quantile(0.25)
                row[f"{col}_iqr_high"] = sub[col].quantile(0.75)
            met = int((sub["fkgl"] <= 6.0).sum())
            row["n_meeting_fkgl6"] = met
            row["pct_meeting_fkgl6"] = 100.0 * met / len(sub)
            lo_m, hi_m = clopper_pearson(met, len(sub))
            row["meeting_ci_low_pct"] = 100 * lo_m
            row["meeting_ci_high_pct"] = 100 * hi_m
            desc_rows.append(row)
        pd.DataFrame(desc_rows).to_csv(REPORTS_DIR / "aim2_post_rewrite_descriptives.csv", index=False)

        across = aim2_across_models(rewrites)
        across.to_csv(REPORTS_DIR / "aim2_across_models.csv", index=False)

        # The analysis plan requires pairwise follow-up after a significant omnibus;
        # previously the pipeline stopped at Friedman, leaving "Claude and Gemini
        # both stronger than GPT-5.5" resting on an omnibus P value alone.
        posthoc = []
        for _, r in across.iterrows():
            if not (r["p"] < 0.05):
                continue
            wide = rewrites.pivot_table(index="page_id", columns="model_id", values=r["score"])
            models = [m for m in ("claude", "openai", "gemini") if m in wide.columns]
            wide = wide.dropna(subset=models)
            posthoc.append(pairwise_posthoc_models(wide, models, label=r["score"]))
        if posthoc:
            pd.concat(posthoc, ignore_index=True).to_csv(
                REPORTS_DIR / "aim2_posthoc_models.csv", index=False)
            log.info("Aim 2: wrote pairwise post-hoc for %d scores", len(posthoc))

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
