"""Aim 3 PRIMARY endpoint — interim analysis of blinded human review.

Reads every reviewer score sheet under data/review/questionnaire_scores/<set>/,
concatenates them (they share one header), joins to the blind key to recover
page_id, procedure, and producing model, and writes per-model descriptives,
inter-rater agreement (for any rewrite scored by >1 reviewer), and the
readability-accuracy trade-off correlation to reports/.

This is a SCREENING/INTERIM view: it summarizes whatever sheets have been
returned so far and is re-runnable as more arrive. It is idempotent and reads
only committed inputs, so its outputs are regeneratable per the repo's
reproducibility floor. It does NOT replace the locked final Aim 3 analysis in
07_run_statistics.py, which expects the complete one-reviewer-per-rewrite table.

Usage:
    .venv/bin/python scripts/12_aim3_human_interim.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import REPORTS_DIR, REVIEW_DIR, SCORES_DIR  # noqa: E402

SCORES_ROOT = REVIEW_DIR / "questionnaire_scores"
BLIND_KEY = REVIEW_DIR / "blind_key.csv"
DELTAS = SCORES_DIR / "deltas.csv"

AXES = ("accuracy_1_5", "completeness_1_5", "added_errors_1_5")
MODEL_ORDER = ["claude", "openai", "gemini"]
MODEL_LABEL = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}


def load_reviews() -> pd.DataFrame:
    files = sorted(SCORES_ROOT.rglob("aim3_scores_*.csv"))
    if not files:
        raise SystemExit(f"No score sheets found under {SCORES_ROOT}")
    frames = []
    for f in files:
        df = pd.read_csv(f)
        df["source_file"] = f.name
        # reviewer role: expert vs layperson from the filename suffix
        stem = f.stem.lower()
        df["reviewer_type"] = "layperson" if "layman" in stem or "layperson" in stem else "expert"
        frames.append(df)
    reviews = pd.concat(frames, ignore_index=True)
    for c in AXES:
        reviews[c] = pd.to_numeric(reviews[c], errors="coerce")
    return reviews


def main() -> None:
    reviews = load_reviews()
    key = pd.read_csv(BLIND_KEY)
    df = reviews.merge(key, on="blind_id", how="left", validate="many_to_one")
    df["procedure"] = df["page_id"].str.split("__").str[1]

    n_reviewers = df["reviewer_name"].nunique()
    n_judgments = len(df)
    print(f"Reviewers: {n_reviewers}  |  Judgments: {n_judgments}")
    print("By set / reviewer_type:")
    print(df.groupby(["set_id", "reviewer_type"])["reviewer_name"].nunique())

    # ---- Per-model descriptives (mean, SD, n) across all judgments so far ----
    desc = (
        df.groupby("model_id")[list(AXES)]
        .agg(["mean", "std", "count"])
        .reindex(MODEL_ORDER)
    )
    desc.to_csv(REPORTS_DIR / "aim3_human_interim_descriptives.csv")
    print("\nPer-model descriptives:\n", desc.round(2))

    # % of accuracy ratings that are maximal (5) and % with no added errors (1)
    summary_rows = []
    for m in MODEL_ORDER:
        sub = df[df["model_id"] == m]
        summary_rows.append(
            {
                "model_id": m,
                "model": MODEL_LABEL[m],
                "n_judgments": len(sub),
                "accuracy_mean": sub["accuracy_1_5"].mean(),
                "completeness_mean": sub["completeness_1_5"].mean(),
                "added_errors_mean": sub["added_errors_1_5"].mean(),
                "pct_accuracy_max": (sub["accuracy_1_5"] == 5).mean() * 100,
                "pct_no_added_error": (sub["added_errors_1_5"] == 1).mean() * 100,
                "n_notes": sub["notes"].notna().sum(),
            }
        )
    summ = pd.DataFrame(summary_rows)
    summ.to_csv(REPORTS_DIR / "aim3_human_interim_summary.csv", index=False)
    print("\nSummary:\n", summ.round(2).to_string(index=False))

    # ---- Inter-rater agreement on rewrites scored by >1 reviewer ----
    dup = df.groupby("blind_id").filter(lambda g: g["reviewer_name"].nunique() > 1)
    irr_rows = []
    if len(dup):
        for axis in AXES:
            piv = dup.pivot_table(index="blind_id", columns="reviewer_name", values=axis, aggfunc="first")
            piv = piv.dropna(axis=1, how="all")
            # pairwise across reviewers who share these items
            cols = [c for c in piv.columns if piv[c].notna().sum() > 0]
            if len(cols) >= 2:
                both = piv[[cols[0], cols[1]]].dropna()
                exact = (both[cols[0]] == both[cols[1]]).mean() * 100
                within1 = ((both[cols[0]] - both[cols[1]]).abs() <= 1).mean() * 100
                irr_rows.append(
                    {
                        "axis": axis,
                        "reviewer_a": cols[0],
                        "reviewer_b": cols[1],
                        "n_items": len(both),
                        "pct_exact_agreement": exact,
                        "pct_within_1": within1,
                    }
                )
    irr = pd.DataFrame(irr_rows)
    if len(irr):
        irr.to_csv(REPORTS_DIR / "aim3_human_interim_irr.csv", index=False)
        print("\nInter-rater agreement (double-scored items):\n", irr.round(1).to_string(index=False))

    # ---- Readability-accuracy trade-off (per-page mean human accuracy vs ΔFKGL) ----
    if DELTAS.exists():
        deltas = pd.read_csv(DELTAS)[["page_id", "model_id", "fkgl_delta"]]
        page_model = (
            df.groupby(["page_id", "model_id"])[list(AXES)].mean().reset_index()
        )
        merged = page_model.merge(deltas, on=["page_id", "model_id"], how="inner")
        tr_rows = []
        for m in MODEL_ORDER:
            sub = merged[merged["model_id"] == m]
            if len(sub) >= 4:
                rho, p = stats.spearmanr(sub["fkgl_delta"], sub["accuracy_1_5"])
                tr_rows.append(
                    {"model_id": m, "model": MODEL_LABEL[m], "n_pages": len(sub), "spearman_rho": rho, "p_value": p}
                )
        if tr_rows:
            tr = pd.DataFrame(tr_rows)
            tr.to_csv(REPORTS_DIR / "aim3_human_interim_tradeoff.csv", index=False)
            print("\nTrade-off (ΔFKGL vs human accuracy):\n", tr.round(3).to_string(index=False))

    print("\nWrote reports/aim3_human_interim_*.csv")


if __name__ == "__main__":
    main()
