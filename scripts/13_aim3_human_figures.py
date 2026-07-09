#!/usr/bin/env python3
"""Figure for the Aim 3 PRIMARY endpoint — interim blinded human review.

Reads the returned reviewer score sheets under
data/review/questionnaire_scores/, joins them to the blind key, and draws a
two-panel figure matching the house style of the automated-panel figures:

  Panel A: per-model mean +/- SD on the three clinical dimensions.
  Panel B: readability reduction vs blinded expert accuracy (per-page scatter,
           large X = model mean), the primary-endpoint version of the trade-off.

Writes reports/figures/aim3_human_interim.png. Re-runnable as more sheets arrive.
This is the INTERIM primary-endpoint figure; it summarizes the reviews returned
so far (experts to date; layperson review pending).
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from src.config import FIGURES_DIR, REVIEW_DIR, SCORES_DIR, ensure_dirs  # noqa: E402

MODELS = ["claude", "openai", "gemini"]
LABELS = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}
COLORS = {"claude": "#4C72B0", "openai": "#55A868", "gemini": "#C44E52"}
AXES = ["accuracy_1_5", "completeness_1_5", "added_errors_1_5"]


def load() -> pd.DataFrame:
    root = REVIEW_DIR / "questionnaire_scores"
    df = pd.concat(
        [pd.read_csv(f) for f in sorted(root.rglob("aim3_scores_*.csv"))],
        ignore_index=True,
    )
    key = pd.read_csv(REVIEW_DIR / "blind_key.csv")
    df = df.merge(key, on="blind_id", how="left")
    for c in AXES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main() -> int:
    ensure_dirs()
    df = load()
    n_rev = df["reviewer_name"].nunique()
    n_judg = len(df)

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5.5))

    # --- Panel A: grouped bars, mean +/- SD, 3 dimensions ---
    dims = [
        ("accuracy_1_5", "Accuracy"),
        ("completeness_1_5", "Completeness"),
        ("added_errors_1_5", "Added errors\n(lower better)"),
    ]
    x = np.arange(len(dims))
    w = 0.25
    for i, m in enumerate(MODELS):
        sub = df[df.model_id == m]
        means = [sub[d].mean() for d, _ in dims]
        sds = [sub[d].std(ddof=1) for d, _ in dims]
        axA.bar(
            x + (i - 1) * w, means, w, yerr=sds, capsize=3,
            label=LABELS[m], color=COLORS[m], alpha=0.9,
        )
    axA.set_xticks(x)
    axA.set_xticklabels([lab for _, lab in dims])
    axA.set_ylabel("Blinded expert score (1–5), mean ± SD")
    axA.set_ylim(0, 5.6)
    axA.axhline(5, color="grey", lw=0.8, ls=":", alpha=0.7)
    axA.set_title("A  Clinical ratings by model", loc="left", fontweight="bold", pad=30)
    axA.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, fontsize=9)

    # --- Panel B: trade-off, reading-level reduction vs expert accuracy ---
    deltas = pd.read_csv(SCORES_DIR / "deltas.csv")[["page_id", "model_id", "fkgl_delta"]]
    page = df.groupby(["page_id", "model_id"])[AXES].mean().reset_index()
    d = page.merge(deltas, on=["page_id", "model_id"], how="inner")
    d["fkgl_reduction"] = -d["fkgl_delta"]
    rng = np.random.default_rng(42)
    for m in MODELS:
        sub = d[d.model_id == m]
        jitter = rng.normal(0, 0.03, len(sub))  # separate overlapping ceiling points
        axB.scatter(
            sub["fkgl_reduction"], sub["accuracy_1_5"] + jitter, s=45, alpha=0.7,
            color=COLORS[m], label=LABELS[m], edgecolor="white", linewidth=0.5,
        )
    for m in MODELS:
        sub = d[d.model_id == m]
        axB.scatter(
            sub["fkgl_reduction"].mean(), sub["accuracy_1_5"].mean(),
            s=320, color=COLORS[m], marker="X", edgecolor="black", linewidth=1.2, zorder=5,
        )
    axB.set_xlabel("Reading-level reduction (FKGL grade levels removed)")
    axB.set_ylabel("Blinded expert accuracy (1–5)")
    axB.set_title("B  Readability reduction vs accuracy", loc="left", fontweight="bold", pad=30)
    axB.legend(loc="lower left", frameon=False, fontsize=8)
    axB.grid(True, alpha=0.25)

    fig.suptitle(
        "Aim 3 primary endpoint (INTERIM): blinded expert review of LLM rewrites",
        fontsize=13, fontweight="bold", y=1.02,
    )
    fig.text(
        0.5, -0.03,
        f"Interim: {n_rev} blinded expert reviewers, {n_judg} ratings to date; "
        "layperson review and remaining expert reads pending. Points jittered vertically to separate ties.",
        ha="center", fontsize=7.5, style="italic",
    )
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_human_interim.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("Wrote", FIGURES_DIR / "aim3_human_interim.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
