#!/usr/bin/env python3
"""Figure: where the three models differ, and where they do not.

The three panels answer the same question with three different measures, and the
contrast between them is the point:

  A  Reading level          -- models differ sharply
  B  Subspecialist judgement -- models do NOT differ
  C  Automated judge panel   -- models differ, but ranked differently from A

Read together this says: the readability gain is real and model-dependent, expert
clinical assessment cannot separate the models, and the automated panel should not
be used as a stand-in for expert review because it disagrees with it.

Significance brackets are drawn only where a pairwise test was actually run, which
happens only after a significant omnibus. Panel B therefore carries no brackets, and
that absence is the finding rather than a gap.
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
from src.config import (  # noqa: E402
    DATA_DIR,
    FIGURE_DPI,
    FIGURES_DIR,
    REPORTS_DIR,
    ensure_dirs,
)

MODELS = ["claude", "openai", "gemini"]
LABEL = {"claude": "Claude\nOpus 4.8", "openai": "GPT-5.5", "gemini": "Gemini\n3.1 Pro"}
COLOR = {"claude": "#3B6EA8", "openai": "#4C9A6B", "gemini": "#C0504D"}
INK, MUTED, RULE = "#22303c", "#5b6b78", "#c9d4dd"


def _p_text(p: float) -> str:
    if p < 0.001:
        return "P < .001"
    return f"P = {p:.3f}".replace("0.", ".") if p < 0.01 else f"P = {p:.2f}".replace("0.", ".")


def _brackets(ax, pairs, ymax, step, color_sig="#1f2d3a"):
    """Draw significance brackets above the bars, lowest pair first."""
    for k, (i, j, p) in enumerate(pairs):
        y = ymax + step * (k + 1)
        sig = p < 0.05
        ax.plot([i, i, j, j], [y - step * 0.22, y, y, y - step * 0.22],
                lw=1.2, color=color_sig if sig else RULE, solid_capstyle="round")
        ax.text((i + j) / 2, y + step * 0.06, _p_text(p) + ("" if sig else " (ns)"),
                ha="center", va="bottom", fontsize=8.6,
                color=INK if sig else MUTED, fontweight="bold" if sig else "normal")


def main() -> int:
    ensure_dirs()
    plt.rcParams.update({
        "figure.dpi": FIGURE_DPI, "font.family": "DejaVu Sans", "font.size": 11,
        "text.color": INK, "axes.labelcolor": INK, "axes.edgecolor": "#c7d0d8",
        "xtick.color": MUTED, "ytick.color": MUTED,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "axes.axisbelow": True,
        "grid.color": "#eef2f6", "grid.linewidth": 0.9,
        "figure.facecolor": "white", "savefig.facecolor": "white",
    })

    rewrites = pd.read_csv(DATA_DIR / "scores" / "rewrites.csv")
    prim = pd.read_csv(REPORTS_DIR / "aim3_compiled_by_model_primary.csv").set_index("model_id")
    cons = pd.read_csv(DATA_DIR / "scores" / "accuracy_llm.csv")
    ph2 = pd.read_csv(REPORTS_DIR / "aim2_posthoc_models.csv")
    ph2 = ph2[ph2.label == "fkgl"]
    amh = pd.read_csv(REPORTS_DIR / "aim3_compiled_across_model.csv").set_index("axis")
    phl_path = REPORTS_DIR / "aim3_llm_posthoc_models.csv"
    phl = pd.read_csv(phl_path) if phl_path.exists() else pd.DataFrame()
    phl = phl[phl.label == "accuracy_1_5"] if len(phl) else phl

    def lookup(tbl, a, b):
        if not len(tbl):
            return None
        r = tbl[((tbl.model_a == a) & (tbl.model_b == b)) | ((tbl.model_a == b) & (tbl.model_b == a))]
        return float(r.iloc[0]["p_holm"]) if len(r) else None

    fig, axes = plt.subplots(1, 3, figsize=(14.6, 5.9))
    x = np.arange(3)

    # ---------------- Panel A: reading level ----------------
    ax = axes[0]
    means = [rewrites[rewrites.model_id == m].fkgl.mean() for m in MODELS]
    sds = [rewrites[rewrites.model_id == m].fkgl.std(ddof=1) for m in MODELS]
    ax.bar(x, means, 0.62, yerr=sds, capsize=4, color=[COLOR[m] for m in MODELS],
           edgecolor="white", linewidth=0.8, error_kw={"elinewidth": 1, "ecolor": "#98a6b2"})
    ax.axhline(6.0, color="#d1495b", lw=1.5, ls=(0, (4, 3)), zorder=1)
    ax.text(2.46, 6.16, "6th-grade target", ha="right", fontsize=8.6, color="#d1495b")
    for i, v in enumerate(means):
        ax.text(i, 0.3, f"{v:.2f}", ha="center", fontsize=10, fontweight="bold", color="white")
    pairs = [(0, 1, lookup(ph2, "claude", "openai")), (1, 2, lookup(ph2, "openai", "gemini")),
             (0, 2, lookup(ph2, "claude", "gemini"))]
    _brackets(ax, [(i, j, p) for i, j, p in pairs if p is not None], max(means) + 1.4, 0.85)
    ax.set_ylim(0, 12.2)
    ax.set_ylabel("Post-rewrite reading level (FKGL)")
    ax.set_title("A   Reading level\nModels differ", loc="left", fontweight="bold", fontsize=12)

    # ---------------- Panel B: subspecialist judgement ----------------
    ax = axes[1]
    m_h = [prim.loc[m, "accuracy_1_5_mean"] for m in MODELS]
    s_h = [prim.loc[m, "accuracy_1_5_sd"] for m in MODELS]
    ax.bar(x, m_h, 0.62, yerr=s_h, capsize=4, color=[COLOR[m] for m in MODELS],
           edgecolor="white", linewidth=0.8, error_kw={"elinewidth": 1, "ecolor": "#98a6b2"})
    for i, v in enumerate(m_h):
        ax.text(i, 1.12, f"{v:.2f}", ha="center", fontsize=10, fontweight="bold", color="white")
    p_omni = float(amh.loc["accuracy_1_5", "p_value"])
    ax.plot([0, 0, 2, 2], [5.42, 5.55, 5.55, 5.42], lw=1.2, color=RULE, solid_capstyle="round")
    ax.text(1, 5.60, f"Friedman {_p_text(p_omni)} (ns)", ha="center", fontsize=8.8, color=MUTED)
    ax.text(1, 6.02, "no pairwise tests run: the overall test was not significant",
            ha="center", fontsize=8.2, color=MUTED, style="italic")
    ax.set_ylim(1, 6.6)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_ylabel("Subspecialist accuracy (1–5), per rewrite")
    ax.set_title("B   Expert clinical judgement\nModels do not differ",
                 loc="left", fontweight="bold", fontsize=12)

    # ---------------- Panel C: automated judge panel ----------------
    ax = axes[2]
    m_l = [cons[cons.model_id == m].accuracy_1_5.mean() for m in MODELS]
    s_l = [cons[cons.model_id == m].accuracy_1_5.std(ddof=1) for m in MODELS]
    ax.bar(x, m_l, 0.62, yerr=s_l, capsize=4, color=[COLOR[m] for m in MODELS],
           edgecolor="white", linewidth=0.8, alpha=0.72,
           error_kw={"elinewidth": 1, "ecolor": "#98a6b2"})
    for i, v in enumerate(m_l):
        ax.text(i, 1.12, f"{v:.2f}", ha="center", fontsize=10, fontweight="bold", color="white")
    pairs_l = [(0, 1, lookup(phl, "claude", "openai")), (1, 2, lookup(phl, "openai", "gemini")),
               (0, 2, lookup(phl, "claude", "gemini"))]
    _brackets(ax, [(i, j, p) for i, j, p in pairs_l if p is not None], 5.18, 0.30)
    ax.set_ylim(1, 6.35)
    ax.set_yticks([1, 2, 3, 4, 5])
    ax.set_ylabel("Automated judge accuracy (1–5)")
    ax.set_title("C   Automated judge panel\nModels differ — but ranked differently",
                 loc="left", fontweight="bold", fontsize=12)

    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels([LABEL[m] for m in MODELS], fontsize=10)

    fig.suptitle("Where the three models differ, and where they do not",
                 fontsize=15, fontweight="bold", y=1.015)
    fig.text(0.5, -0.045,
             "Bars show mean ± SD. Brackets are Holm-adjusted paired Wilcoxon tests, drawn only "
             "where a significant overall test permitted pairwise testing.\n"
             "Panel C is an exploratory screening analysis: it ranks GPT-5.5 highest and Gemini "
             "lowest, a ranking the blinded subspecialist review in panel B does not reproduce.",
             ha="center", fontsize=9, color=MUTED, style="italic")
    fig.tight_layout()
    out = FIGURES_DIR / "model_comparison_overview.png"
    fig.savefig(out, bbox_inches="tight")
    plt.close(fig)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
