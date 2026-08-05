#!/usr/bin/env python3
"""Figures for the compiled Aim 3 human-review results (interim).

  reports/figures/aim3_human_compiled.png   two panels: per-model clinical
        ratings by blinded experts (labeled instrument) + the readability-accuracy
        trade-off (grade levels removed vs expert accuracy).
  reports/figures/aim3_presentation_bias.png   per-model expert accuracy under the
        standard (labeled) vs neutral-presentation instrument.

House style matches the automated-panel and interim figures.
"""
from __future__ import annotations

import sys
from itertools import combinations  # noqa: F401  (kept parallel to stats script)
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
    frames = []
    for f in sorted((REVIEW_DIR / "questionnaire_scores").rglob("aim3_scores_*.csv")):
        d = pd.read_csv(f)
        s = f.stem.lower()
        d["reviewer_type"] = "layperson" if ("layman" in s or "layperson" in s) else "expert"
        d["presentation"] = "neutral" if "neutral" in s else "standard"
        frames.append(d)
    df = pd.concat(frames, ignore_index=True).merge(
        pd.read_csv(REVIEW_DIR / "blind_key.csv"), on="blind_id", how="left")
    for c in AXES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["condition"] = np.where(
        df.reviewer_type == "layperson", "layperson",
        np.where(df.presentation == "neutral", "expert_neutral", "expert_labeled"))
    return df


def fig_compiled(df: pd.DataFrame) -> None:
    lab = df[df.condition == "expert_labeled"]
    n_rev, n_rat = lab.reviewer_name.nunique(), len(lab)
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13, 5.6))

    dims = [("accuracy_1_5", "Accuracy"), ("completeness_1_5", "Completeness"),
            ("added_errors_1_5", "Added errors\n(lower better)")]
    x = np.arange(len(dims))
    w = 0.25
    for i, m in enumerate(MODELS):
        sub = lab[lab.model_id == m]
        means = [sub[d].mean() for d, _ in dims]
        sds = [sub[d].std(ddof=1) for d, _ in dims]
        axA.bar(x + (i - 1) * w, means, w, yerr=sds, capsize=3, label=LABELS[m],
                color=COLORS[m], alpha=0.9)
    axA.set_xticks(x)
    axA.set_xticklabels([lab_ for _, lab_ in dims])
    axA.set_ylabel("Blinded expert score (1–5), mean ± SD")
    axA.set_ylim(0, 5.6)
    axA.axhline(5, color="grey", lw=0.8, ls=":", alpha=0.7)
    axA.set_title("A  Clinical ratings by model", loc="left", fontweight="bold", pad=30)
    axA.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, frameon=False, fontsize=9)

    deltas = pd.read_csv(SCORES_DIR / "deltas.csv")[["page_id", "model_id", "fkgl_delta"]]
    pm = lab.groupby(["page_id", "model_id"])[AXES].mean().reset_index().merge(
        deltas, on=["page_id", "model_id"])
    pm["reduction"] = -pm["fkgl_delta"]
    rng = np.random.default_rng(42)
    for m in MODELS:
        s = pm[pm.model_id == m]
        jit = rng.normal(0, 0.03, len(s))
        axB.scatter(s["reduction"], s["accuracy_1_5"] + jit, s=45, alpha=0.7,
                    color=COLORS[m], label=LABELS[m], edgecolor="white", linewidth=0.5)
    for m in MODELS:
        s = pm[pm.model_id == m]
        axB.scatter(s["reduction"].mean(), s["accuracy_1_5"].mean(), s=320, color=COLORS[m],
                    marker="X", edgecolor="black", linewidth=1.2, zorder=5)
    axB.set_xlabel("Reading-level reduction (FKGL grade levels removed)")
    axB.set_ylabel("Blinded expert accuracy (1–5)")
    axB.set_title("B  Readability reduction vs accuracy", loc="left", fontweight="bold", pad=30)
    axB.legend(loc="lower left", frameon=False, fontsize=8)
    axB.grid(True, alpha=0.25)

    fig.suptitle("Aim 3 primary endpoint (INTERIM): blinded subspecialist review of LLM rewrites",
                 fontsize=13, fontweight="bold", y=1.02)
    fig.text(0.5, -0.03,
             f"Interim: {n_rev} subspecialist reviewers, {n_rat} ratings, all 77 rewrites covered; "
             "labeled instrument. Points jittered vertically to separate ties.",
             ha="center", fontsize=7.5, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_human_compiled.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def fig_bias(df: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8, 5.2))
    conds = [("expert_labeled", "Standard (labeled AI rewrite)"),
             ("expert_neutral", "Neutral presentation")]
    x = np.arange(len(MODELS))
    w = 0.38
    for j, (c, name) in enumerate(conds):
        means, sds = [], []
        for m in MODELS:
            s = df[(df.condition == c) & (df.model_id == m)].accuracy_1_5
            means.append(s.mean())
            sds.append(s.std(ddof=1))
        ax.bar(x + (j - 0.5) * w, means, w, yerr=sds, capsize=3, label=name,
               color=("#3a5a80" if j == 0 else "#9db8d6"), alpha=0.95)
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[m] for m in MODELS])
    ax.set_ylabel("Blinded expert accuracy (1–5), mean ± SD")
    ax.set_ylim(3.8, 5.15)
    ax.set_title("Presentation effect on expert accuracy scoring", pad=30, fontweight="bold")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, frameon=False, fontsize=9)
    ax.figure.text(0.5, -0.02,
                   "Between-reviewer comparison (different subspecialists per instrument); the label "
                   "effect is therefore confounded with rater identity.",
                   ha="center", fontsize=7.5, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_presentation_bias.png", dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ensure_dirs()
    df = load()
    fig_compiled(df)
    fig_bias(df)
    print("wrote reports/figures/aim3_human_compiled.png and aim3_presentation_bias.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
