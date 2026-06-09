#!/usr/bin/env python3
"""Figures for the Aim 3 automated LLM-judge panel (SECONDARY analysis).

Writes:
  reports/figures/aim3_llm_scores_by_model.png   grouped bars, 3 dimensions x 3 models
  reports/figures/aim3_llm_tradeoff.png          reading-level reduction vs consensus accuracy
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from src.config import FIGURES_DIR, SCORES_DIR, ensure_dirs  # noqa: E402

MODELS = ["claude", "openai", "gemini"]
LABELS = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}
COLORS = {"claude": "#4C72B0", "openai": "#55A868", "gemini": "#C44E52"}


def main() -> int:
    ensure_dirs()
    cons = pd.read_csv(SCORES_DIR / "accuracy_llm.csv")
    deltas = pd.read_csv(SCORES_DIR / "deltas.csv")

    # --- Figure A: grouped bars, mean +/- SD, 3 dimensions ---
    dims = [("accuracy_1_5", "Accuracy"), ("completeness_1_5", "Completeness"),
            ("added_errors_1_5", "Added errors\n(lower better)")]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(len(dims))
    w = 0.25
    for i, m in enumerate(MODELS):
        sub = cons[cons.model_id == m]
        means = [sub[d].mean() for d, _ in dims]
        sds = [sub[d].std(ddof=1) for d, _ in dims]
        ax.bar(x + (i - 1) * w, means, w, yerr=sds, capsize=3,
               label=LABELS[m], color=COLORS[m], alpha=0.9)
    ax.set_xticks(x)
    ax.set_xticklabels([lab for _, lab in dims])
    ax.set_ylabel("Consensus score (1–5), mean ± SD")
    ax.set_ylim(0, 5.5)
    ax.set_title("Aim 3 (automated LLM-judge panel): rewrite fidelity by model")
    ax.legend(loc="lower center", ncol=3, frameon=False, fontsize=8)
    ax.figure.text(0.5, -0.02, "Automated 3-LLM-judge screen; not the primary human subspecialist review.",
                   ha="center", fontsize=7, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_llm_scores_by_model.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    # --- Figure B: trade-off, reading-level reduction vs consensus accuracy ---
    d = deltas[["page_id", "model_id", "fkgl_delta"]].merge(cons, on=["page_id", "model_id"])
    d["fkgl_reduction"] = -d["fkgl_delta"]  # positive = grade levels removed
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    for m in MODELS:
        sub = d[d.model_id == m]
        ax.scatter(sub["fkgl_reduction"], sub["accuracy_1_5"], s=45, alpha=0.7,
                   color=COLORS[m], label=LABELS[m], edgecolor="white", linewidth=0.5)
    # model centroids
    for m in MODELS:
        sub = d[d.model_id == m]
        ax.scatter(sub["fkgl_reduction"].mean(), sub["accuracy_1_5"].mean(),
                   s=320, color=COLORS[m], marker="X", edgecolor="black", linewidth=1.2, zorder=5)
    ax.set_xlabel("Reading-level reduction (FKGL grade levels removed)")
    ax.set_ylabel("Consensus accuracy (1–5)")
    ax.set_title("Readability reduction vs medical-accuracy fidelity\n(large X = model mean)")
    ax.legend(loc="lower left", frameon=False, fontsize=8)
    ax.grid(True, alpha=0.25)
    ax.figure.text(0.5, -0.02, "Automated 3-LLM-judge screen; accuracy is preliminary pending blinded subspecialist review.",
                   ha="center", fontsize=7, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_llm_tradeoff.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("wrote reports/figures/aim3_llm_scores_by_model.png and aim3_llm_tradeoff.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
