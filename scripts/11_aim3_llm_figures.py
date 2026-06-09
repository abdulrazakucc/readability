#!/usr/bin/env python3
"""Figures for the Aim 3 automated LLM-judge panel (SECONDARY analysis).

Writes:
  reports/figures/aim3_llm_scores_by_model.png   grouped bars, 3 dimensions x 3 models
  reports/figures/aim3_llm_tradeoff.png          reading-level reduction vs consensus accuracy (scatter)
  reports/figures/aim3_llm_tradeoff_alt.png      same trade-off as a paired dual-axis summary
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
    ax.set_title("Aim 3 (automated LLM-judge panel): rewrite fidelity by model", pad=34)
    # Legend above the plot so it never sits over the bars.
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3,
              frameon=False, fontsize=9)
    ax.figure.text(0.5, -0.04, "Automated 3-LLM-judge screen; not the primary human subspecialist review.",
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

    # --- Figure C: same trade-off, different encoding ---------------------
    # Paired dual-axis summary: per model, a bar for mean reading-level
    # reduction (left axis) and a marker+line for mean consensus accuracy
    # (right axis). Models are ordered by how aggressively they simplify, so
    # the diverging readability-up / accuracy-down pattern reads at a glance.
    summ = (d.groupby("model_id")
              .agg(red_mean=("fkgl_reduction", "mean"),
                   red_sd=("fkgl_reduction", "std"),
                   acc_mean=("accuracy_1_5", "mean"),
                   acc_sd=("accuracy_1_5", "std"))
              .reindex(["openai", "claude", "gemini"]))  # least -> most simplified
    order = list(summ.index)
    xs = np.arange(len(order))

    fig, ax1 = plt.subplots(figsize=(8, 5.5))
    bars = ax1.bar(xs, summ["red_mean"], width=0.55,
                   yerr=summ["red_sd"], capsize=4,
                   color=[COLORS[m] for m in order], alpha=0.55,
                   edgecolor="black", linewidth=0.6, zorder=2)
    ax1.set_ylabel("Reading-level reduction\n(FKGL grade levels removed, mean ± SD)", fontsize=10)
    ax1.set_ylim(0, 8)
    ax1.set_xticks(xs)
    ax1.set_xticklabels([LABELS[m] for m in order])
    for b, v in zip(bars, summ["red_mean"]):
        ax1.text(b.get_x() + b.get_width() / 2, 0.25, f"{v:.1f} grades",
                 ha="center", va="bottom", fontsize=9, fontweight="bold",
                 color="#222222")

    ax2 = ax1.twinx()
    ax2.errorbar(xs, summ["acc_mean"], yerr=summ["acc_sd"], color="black",
                 marker="D", markersize=9, markerfacecolor="white",
                 markeredgewidth=1.6, linewidth=1.8, capsize=4, zorder=5)
    ax2.set_ylabel("Consensus accuracy (1–5), mean ± SD", fontsize=10)
    ax2.set_ylim(4.0, 5.15)
    for xi, v in zip(xs, summ["acc_mean"]):
        ax2.annotate(f"{v:.2f}", (xi, v), textcoords="offset points",
                     xytext=(10, 6), fontsize=9, fontweight="bold")

    ax1.set_title("The readability–accuracy trade-off across models\n"
                  "(bars: simplification achieved · diamonds: medical-accuracy fidelity)",
                  fontsize=12)
    ax1.set_axisbelow(True)
    ax1.grid(axis="y", alpha=0.2)
    fig.text(0.5, -0.03,
             "More simplification (left→right) tracks lower accuracy fidelity. "
             "Automated 3-LLM-judge screen; pending blinded subspecialist review.",
             ha="center", fontsize=7, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_llm_tradeoff_alt.png", dpi=150, bbox_inches="tight")
    plt.close(fig)

    print("wrote reports/figures/aim3_llm_scores_by_model.png, "
          "aim3_llm_tradeoff.png and aim3_llm_tradeoff_alt.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
