#!/usr/bin/env python3
"""Generate manuscript-ready figures from scored CSVs.

Figures:
  aim1_score_by_site.png       — boxplot of FKGL by site
  aim1_score_by_procedure.png  — boxplot of FKGL by procedure
  aim2_delta_by_model.png      — boxplot of FKGL deltas by model
  aim3_tradeoff.png            — scatter: FKGL drop vs accuracy, by model

All figures are auto-generated; do not hand-edit. Re-running this script overwrites them.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import FIGURES_DIR, SCORES_DIR, ensure_dirs  # noqa: E402

log = logging.getLogger("figures")


def _save(fig, name: str) -> Path:
    out = FIGURES_DIR / name
    fig.savefig(out, dpi=300, bbox_inches="tight")
    plt.close(fig)
    log.info("wrote %s", out)
    return out


def aim1_figures(originals: pd.DataFrame) -> None:
    sns.set_style("whitegrid")
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.boxplot(data=originals, x="site", y="fkgl", ax=ax)
    ax.axhline(6.0, color="red", linestyle="--", label="6th-grade benchmark")
    ax.set_title("Aim 1 — FKGL by website (original pages)")
    ax.set_ylabel("Flesch–Kincaid Grade Level")
    ax.legend()
    plt.xticks(rotation=30, ha="right")
    _save(fig, "aim1_fkgl_by_site.png")

    fig, ax = plt.subplots(figsize=(6, 5))
    sns.boxplot(data=originals, x="procedure", y="fkgl", ax=ax)
    ax.axhline(6.0, color="red", linestyle="--", label="6th-grade benchmark")
    ax.set_title("Aim 1 — FKGL by procedure")
    ax.set_ylabel("Flesch–Kincaid Grade Level")
    ax.legend()
    _save(fig, "aim1_fkgl_by_procedure.png")


def aim2_figures(deltas: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.boxplot(data=deltas, x="model_id", y="fkgl_delta", ax=ax)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Aim 2 — FKGL change (rewrite − original) by model")
    ax.set_ylabel("Δ FKGL (negative = easier)")
    _save(fig, "aim2_fkgl_delta_by_model.png")


def aim3_figures(deltas: pd.DataFrame, accuracy: pd.DataFrame) -> None:
    merged = deltas.merge(accuracy, on=["page_id", "model_id"])
    fig, ax = plt.subplots(figsize=(7, 5))
    for model_id, sub in merged.groupby("model_id"):
        ax.scatter(sub["fkgl_delta"], sub["accuracy_1_5"], label=model_id, alpha=0.7)
    ax.axhline(3, color="grey", linestyle="--", linewidth=0.7)
    ax.axvline(0, color="grey", linestyle="--", linewidth=0.7)
    ax.set_xlabel("Δ FKGL (negative = easier)")
    ax.set_ylabel("Accuracy (1–5)")
    ax.set_title("Aim 3 — reading-level drop vs accuracy")
    ax.legend(title="Model")
    _save(fig, "aim3_tradeoff.png")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--originals", default=str(SCORES_DIR / "originals.csv"))
    parser.add_argument("--deltas", default=str(SCORES_DIR / "deltas.csv"))
    parser.add_argument("--accuracy", default=str(SCORES_DIR / "accuracy.csv"))
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()

    if Path(args.originals).exists():
        aim1_figures(pd.read_csv(args.originals))
    if Path(args.deltas).exists():
        aim2_figures(pd.read_csv(args.deltas))
    if Path(args.deltas).exists() and Path(args.accuracy).exists():
        aim3_figures(pd.read_csv(args.deltas), pd.read_csv(args.accuracy))
    return 0


if __name__ == "__main__":
    sys.exit(main())
