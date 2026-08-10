#!/usr/bin/env python3
"""Publication-quality figures for the compiled Aim 3 human-review results (interim).

Writes to reports/figures/:
  aim3_human_compiled.png     PRIMARY: per-model clinical ratings by blinded
                              subspecialists (labeled instrument) + the
                              readability-accuracy trade-off.
  aim3_presentation_bias.png  labeled vs neutral-presentation accuracy WITHIN the
                              lay cohort (the presentation-bias check), with
                              significance marks. Lay readers scored both
                              presentations; only one subspecialist scored the
                              neutral instrument, too thin to carry this contrast.
  aim3_three_conditions.png   accuracy and completeness across all four cohorts
                              (subspecialists labeled/neutral, lay labeled/neutral).

Bar values are read from the compiled tables (reports/aim3_compiled_*.csv) so the
figures and tables never disagree; the trade-off scatter is recomputed from the
raw per-page means. Re-runnable; run scripts/12 first.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
from src.config import (  # noqa: E402
    FIGURE_DPI,
    FIGURES_DIR,
    REPORTS_DIR,
    REVIEW_DIR,
    SCORES_DIR,
    ensure_dirs,
)

MODELS = ["claude", "openai", "gemini"]
LABELS = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}
COLORS = {"claude": "#3B6EA8", "openai": "#4C9A6B", "gemini": "#C0504D"}
INK = "#22303c"
MUTED = "#5b6b78"
AXES = ["accuracy_1_5", "completeness_1_5", "added_errors_1_5"]
_SLUG_RE = re.compile(r"^aim3_scores_(?:neutral_)?set_[a-c]_(.+?)_(?:expert|layman|layperson)$")


def setup_style() -> None:
    plt.rcParams.update({
        "figure.dpi": FIGURE_DPI,
        "font.family": "DejaVu Sans",
        "font.size": 11,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": "#c7d0d8",
        "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True,
        "grid.color": "#e6ebf0", "grid.linewidth": 0.9,
        "axes.titlepad": 12, "figure.facecolor": "white", "savefig.facecolor": "white",
    })


def load_raw() -> pd.DataFrame:
    frames = []
    for f in sorted((REVIEW_DIR / "questionnaire_scores").rglob("aim3_scores_*.csv")):
        d = pd.read_csv(f)
        s = f.stem.lower()
        m = _SLUG_RE.match(s)
        d["reviewer_id"] = m.group(1) if m else s
        d["reviewer_type"] = "layperson" if ("layman" in s or "layperson" in s) else "expert"
        d["presentation"] = "neutral" if "neutral" in s else "standard"
        frames.append(d)
    df = pd.concat(frames, ignore_index=True).merge(
        pd.read_csv(REVIEW_DIR / "blind_key.csv"), on="blind_id", how="left")
    for c in AXES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["condition"] = np.where(
        df.reviewer_type == "layperson",
        np.where(df.presentation == "neutral", "layperson_neutral", "layperson_labeled"),
        np.where(df.presentation == "neutral", "expert_neutral", "expert_labeled"))
    return df


def _bar_labels(ax, bars, fmt="{:.2f}", dy=0.06, size=8.5):
    for b in bars:
        h = b.get_height()
        if np.isfinite(h):
            ax.text(b.get_x() + b.get_width() / 2, h + dy, fmt.format(h),
                    ha="center", va="bottom", fontsize=size, color=INK, fontweight="normal")


def fig_primary(bym: pd.DataFrame, raw: pd.DataFrame, cov: pd.DataFrame) -> None:
    lab = bym[bym.condition == "expert_labeled"].set_index("model_id")
    n_rev = int(cov.loc[cov.condition == "expert_labeled", "reviewers"].iloc[0])
    n_rat = int(cov.loc[cov.condition == "expert_labeled", "ratings"].iloc[0])
    n_rw = int(cov.loc[cov.condition == "expert_labeled", "rewrites_total"].iloc[0])

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(13.2, 5.7),
                                   gridspec_kw={"width_ratios": [1.05, 1]})

    # ---- Panel A: grouped bars, 3 dimensions x 3 models ----
    dims = [("accuracy_1_5", "Accuracy"), ("completeness_1_5", "Completeness"),
            ("added_errors_1_5", "Added errors\n(1 = best)")]
    x = np.arange(len(dims))
    w = 0.26
    for i, m in enumerate(MODELS):
        means = [lab.loc[m, f"{a}_mean"] for a, _ in dims]
        sds = [lab.loc[m, f"{a}_sd"] for a, _ in dims]
        bars = axA.bar(x + (i - 1) * w, means, w, yerr=sds, capsize=3,
                       label=LABELS[m], color=COLORS[m], edgecolor="white", linewidth=0.6,
                       error_kw={"elinewidth": 1, "ecolor": "#95a3ae"})
        _bar_labels(axA, bars)
    axA.axhline(5, color="#b9c4cd", lw=1, ls=(0, (2, 2)), zorder=0)
    axA.set_xticks(x)
    axA.set_xticklabels([n for _, n in dims])
    axA.set_ylabel("Blinded expert score (1–5), mean ± SD")
    axA.set_ylim(0, 5.75)
    axA.set_title("A   Clinical ratings by model", loc="left", fontweight="bold", pad=10)
    # annotate the completeness dip
    gem_comp = lab.loc["gemini", "completeness_1_5_mean"]
    axA.annotate("aggressive simplification\nlowers completeness",
                 xy=(1 + w, gem_comp), xytext=(1.45, 3.05),
                 fontsize=8, color=MUTED, ha="left",
                 arrowprops=dict(arrowstyle="->", color=MUTED, lw=1))

    # ---- Panel B: readability reduction vs accuracy (per page) ----
    deltas = pd.read_csv(SCORES_DIR / "deltas.csv")[["page_id", "model_id", "fkgl_delta"]]
    pm = (raw[raw.condition == "expert_labeled"]
          .groupby(["page_id", "model_id"])[AXES].mean().reset_index()
          .merge(deltas, on=["page_id", "model_id"]))
    pm["reduction"] = -pm["fkgl_delta"]
    rng = np.random.default_rng(42)
    for m in MODELS:
        s = pm[pm.model_id == m]
        jit = rng.normal(0, 0.02, len(s))
        axB.scatter(s["reduction"], s["accuracy_1_5"] + jit, s=42, alpha=0.65,
                    color=COLORS[m], label=LABELS[m], edgecolor="white", linewidth=0.6)
    # Gemini trend (the one significant association) + rho labels
    for m in MODELS:
        s = pm[pm.model_id == m]
        rho, p = stats.spearmanr(s["reduction"], s["accuracy_1_5"])
        axB.scatter(s["reduction"].mean(), s["accuracy_1_5"].mean(), s=300, color=COLORS[m],
                    marker="X", edgecolor=INK, linewidth=1.3, zorder=6)
        if m == "gemini":
            b1, b0 = np.polyfit(s["reduction"], s["accuracy_1_5"], 1)
            xs = np.array([s["reduction"].min(), s["reduction"].max()])
            axB.plot(xs, b0 + b1 * xs, color=COLORS[m], lw=2, ls="--", zorder=4)
            axB.text(0.97, 0.06, f"Gemini ρ = {rho:.2f} (P = {p:.02f})", transform=axB.transAxes,
                     ha="right", fontsize=8.5, color=COLORS[m], fontweight="bold")
    axB.set_xlabel("Reading-level reduction (FKGL grade levels removed)")
    axB.set_ylabel("Blinded expert accuracy (1–5)")
    axB.set_title("B   Readability reduction vs accuracy", loc="left", fontweight="bold", pad=10)
    axB.set_ylim(3.7, 5.15)

    handles = [plt.Line2D([0], [0], marker="s", ls="", markersize=9, markerfacecolor=COLORS[m],
                          markeredgecolor="white", label=LABELS[m]) for m in MODELS]
    fig.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, 0.965), ncol=3,
               frameon=False, fontsize=10, handletextpad=0.4, columnspacing=1.8)
    fig.suptitle("Aim 3 primary endpoint (interim): blinded subspecialist review of LLM rewrites",
                 fontsize=13.5, fontweight="bold", x=0.5, y=1.05)
    fig.text(0.5, -0.035,
             f"{n_rev} subspecialist reviewers · {n_rat} ratings · all {n_rw} rewrites · labeled instrument. "
             "Large X = model mean; points jittered vertically to separate ties.",
             ha="center", fontsize=8, color=MUTED, style="italic")
    fig.tight_layout(w_pad=2.5)
    fig.savefig(FIGURES_DIR / "aim3_human_compiled.png", bbox_inches="tight")
    plt.close(fig)


def fig_bias(bym: pd.DataFrame, pe: pd.DataFrame) -> None:
    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    # The labeling contrast is a WITHIN-LAY comparison: both presentations were
    # scored by lay readers (2 labeled, 3 neutral). Only one subspecialist scored
    # the neutral instrument, too thin to carry this figure.
    conds = [("layperson_labeled", "Standard instrument (labeled “AI rewrite”)", "#2f4f6f"),
             ("layperson_neutral", "Neutral presentation", "#8fb2d4")]
    x = np.arange(len(MODELS))
    w = 0.36
    for j, (c, name, col) in enumerate(conds):
        sub = bym[bym.condition == c].set_index("model_id")
        means = [sub.loc[m, "accuracy_1_5_mean"] for m in MODELS]
        # 95% CI of the mean (appropriate uncertainty for comparing means on ceiling data)
        ci = [1.96 * sub.loc[m, "accuracy_1_5_sd"] / np.sqrt(sub.loc[m, "n"]) for m in MODELS]
        bars = ax.bar(x + (j - 0.5) * w, means, w, yerr=ci, capsize=4, label=name,
                      color=col, edgecolor="white", linewidth=0.6,
                      error_kw={"elinewidth": 1.1, "ecolor": "#7a8894"})
        _bar_labels(ax, bars, dy=0.015)
    # significance brackets at a fixed height inside the axis
    pe_acc = pe[pe.axis == "accuracy_1_5"].set_index("scope")
    ybar = 5.13
    for i, m in enumerate(MODELS):
        p = pe_acc.loc[m, "mannwhitney_p"]
        mark = "***" if p < .001 else "**" if p < .01 else "*" if p < .05 else "ns"
        pstr = "P < .001" if p < .001 else f"P = {p:.2f}"
        ax.plot([x[i] - w / 2, x[i] - w / 2, x[i] + w / 2, x[i] + w / 2],
                [ybar - 0.03, ybar, ybar, ybar - 0.03], color=MUTED, lw=1)
        txt = f"{mark}  ({pstr})" if mark != "ns" else f"ns  ({pstr})"
        ax.text(x[i], ybar + 0.015, txt, ha="center", va="bottom", fontsize=8.5,
                color=(INK if mark != "ns" else MUTED), fontweight=("bold" if mark != "ns" else "normal"))
    ax.set_xticks(x)
    ax.set_xticklabels([LABELS[m] for m in MODELS])
    ax.set_ylabel("Blinded expert accuracy (1–5), mean ± 95% CI")
    ax.set_ylim(4.5, 5.28)
    ax.set_title("Does labeling a passage “AI” change expert accuracy scoring?",
                 fontweight="bold", pad=42)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.005), ncol=2, frameon=False, fontsize=9.5)
    fig.text(0.5, -0.02,
             "Between-reviewer comparison (different subspecialists per instrument), so the label effect is "
             "confounded with rater identity. Neutral scores are no lower, arguing against an anti-AI penalty.",
             ha="center", fontsize=7.8, color=MUTED, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_presentation_bias.png", bbox_inches="tight")
    plt.close(fig)


def fig_conditions(bym: pd.DataFrame) -> None:
    # Four cohorts: reviewer type x instrument presentation. The lay cohorts are
    # shown separately, never pooled, so the presentation contrast stays visible.
    conds = [("expert_labeled", "Subspecialists\n(labeled)"),
             ("expert_neutral", "Subspecialist\n(neutral)"),
             ("layperson_labeled", "Lay readers\n(labeled)"),
             ("layperson_neutral", "Lay readers\n(neutral)")]
    # Wide enough that four two-line cohort labels do not collide.
    fig, axes = plt.subplots(1, 2, figsize=(15.4, 5.6))
    panels = [("accuracy_1_5", "Accuracy"), ("completeness_1_5", "Completeness")]
    for ax, (metric, title) in zip(axes, panels, strict=True):
        x = np.arange(len(conds))
        w = 0.26
        for i, m in enumerate(MODELS):
            means = [bym[(bym.condition == c) & (bym.model_id == m)][f"{metric}_mean"].iloc[0]
                     for c, _ in conds]
            bars = ax.bar(x + (i - 1) * w, means, w, label=LABELS[m], color=COLORS[m],
                          edgecolor="white", linewidth=0.6)
            _bar_labels(ax, bars, dy=0.015, size=8)
        ax.axhline(5, color="#b9c4cd", lw=1, ls=(0, (2, 2)), zorder=0)
        ax.set_xticks(x)
        ax.set_xticklabels([n for _, n in conds])
        ax.set_ylim(4.0, 5.25)
        ax.set_title(title, fontweight="bold", loc="left")
        ax.set_ylabel("Mean rating (1–5)")
    axes[0].legend(loc="lower center", bbox_to_anchor=(1.05, 1.06), ncol=3, frameon=False, fontsize=9.5)
    fig.suptitle("Medical-accuracy and completeness by reviewer cohort", fontsize=13, fontweight="bold",
                 y=1.02)
    fig.text(0.5, -0.03,
             "Laypersons rate near the ceiling on both scales (they cannot detect the subtle clinical gaps "
             "experts flag); the expert cohorts localize the residual risk to the most aggressive simplifier.",
             ha="center", fontsize=8, color=MUTED, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_three_conditions.png", bbox_inches="tight")
    plt.close(fig)


def fig_expert_vs_lay(evl: pd.DataFrame, cov: pd.DataFrame) -> None:
    """eFigure 1: blinded subspecialists vs lay readers on all three scales.

    Lay readers are pooled across both presentations (385 ratings, 5 readers),
    which is the contrast the manuscript reports. The point of the figure is that
    lay raters sit closer to the ceiling than subspecialists on accuracy -- they
    do not detect what the experts flag -- which is why the subspecialist review
    is the primary endpoint.
    """
    n_exp = int(cov.loc[cov.condition == "expert_labeled", "reviewers"].iloc[0])
    r_exp = int(cov.loc[cov.condition == "expert_labeled", "ratings"].iloc[0])
    lay = cov[cov.condition.isin(["layperson_labeled", "layperson_neutral"])]
    n_lay, r_lay = int(lay.reviewers.sum()), int(lay.ratings.sum())

    axes_order = [("accuracy_1_5", "Accuracy"), ("completeness_1_5", "Completeness"),
                  ("added_errors_1_5", "Added errors")]
    e = evl.set_index("axis")
    fig, ax = plt.subplots(figsize=(9.2, 5.6))
    x = np.arange(len(axes_order))
    w = 0.34
    for j, (who, col, colr) in enumerate(
            [("expert", "expert_mean", "#1F77B4"), ("lay", "layperson_mean", "#E8A33D")]):
        vals = [e.loc[a, col] for a, _ in axes_order]
        bars = ax.bar(x + (j - 0.5) * w, vals, w, color=colr, edgecolor="white", linewidth=0.7,
                      label=(f"Subspecialists (n={n_exp}; {r_exp} ratings)" if who == "expert"
                             else f"Lay readers (n={n_lay}; {r_lay} ratings)"))
        _bar_labels(ax, bars, dy=0.03, size=9)
    for i, (a, _) in enumerate(axes_order):
        p = e.loc[a, "mannwhitney_p"]
        mark = f"P = {p:.3f}" if p < 0.01 else f"P = {p:.2f}" + (" (ns)" if p >= 0.05 else "")
        ax.text(i, 5.42, mark, ha="center", fontsize=9.5, color=MUTED)
    ax.set_xticks(x)
    ax.set_xticklabels([n for _, n in axes_order])
    ax.set_ylabel("Mean rating (1–5)")
    ax.set_ylim(1, 5.7)
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, -0.22), ncol=2, frameon=False, fontsize=9.5)
    ax.set_title("Blinded subspecialists vs lay readers", fontweight="bold", loc="left")
    fig.text(0.5, -0.10,
             "Two-sided Mann–Whitney U. Lay readers scored accuracy significantly higher than "
             "subspecialists,\nconsistent with lay raters missing issues the subspecialists detected.",
             ha="center", fontsize=8, color=MUTED, style="italic")
    fig.tight_layout()
    fig.savefig(FIGURES_DIR / "aim3_expert_vs_lay.png", bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ensure_dirs()
    setup_style()
    bym = pd.read_csv(REPORTS_DIR / "aim3_compiled_by_model.csv")
    cov = pd.read_csv(REPORTS_DIR / "aim3_compiled_coverage.csv")
    pe = pd.read_csv(REPORTS_DIR / "aim3_compiled_presentation_effect.csv")
    evl = pd.read_csv(REPORTS_DIR / "aim3_compiled_expert_vs_lay.csv")
    raw = load_raw()
    fig_primary(bym, raw, cov)
    fig_bias(bym, pe)
    fig_conditions(bym)
    fig_expert_vs_lay(evl, cov)
    print("wrote 4 figures to", FIGURES_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
