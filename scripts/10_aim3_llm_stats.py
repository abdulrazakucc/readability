#!/usr/bin/env python3
"""Aim 3 SECONDARY statistics on the automated LLM-judge panel.

Reads data/scores/accuracy_llm_raw.csv (one row per page x model x judge) and
accuracy_llm.csv (consensus = mean across judges), joins to deltas.csv, and writes:

  reports/aim3_llm_descriptives.csv     per-model consensus mean/SD per dimension
  reports/aim3_llm_model_comparison.csv Friedman across models per dimension (consensus)
  reports/aim3_llm_interjudge.csv       inter-judge agreement per dimension
  reports/aim3_llm_self_preference.csv  each judge's own-model vs other-model mean (bias check)
  reports/aim3_llm_tradeoff.csv         Spearman(Δ reading-level, accuracy/completeness) per model

These are automated screening results, NOT the human subspecialist endpoint.
"""

from __future__ import annotations

import logging
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import REPORTS_DIR, SCORES_DIR, ensure_dirs  # noqa: E402
from src.stats import aim3_clinical_model_comparison, aim3_tradeoff_correlations  # noqa: E402

log = logging.getLogger("aim3-llm")
DIMS = ["accuracy_1_5", "completeness_1_5", "added_errors_1_5"]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ensure_dirs()
    raw = pd.read_csv(SCORES_DIR / "accuracy_llm_raw.csv")
    cons = pd.read_csv(SCORES_DIR / "accuracy_llm.csv")
    deltas = pd.read_csv(SCORES_DIR / "deltas.csv")

    # 1. Per-model consensus descriptives
    rows = []
    for m, s in cons.groupby("model_id"):
        for d in DIMS:
            rows.append({"model_id": m, "dimension": d, "n": len(s),
                         "mean": round(s[d].mean(), 3), "sd": round(s[d].std(ddof=1), 3),
                         "median": s[d].median()})
    pd.DataFrame(rows).to_csv(REPORTS_DIR / "aim3_llm_descriptives.csv", index=False)

    # 2. Friedman across models on consensus (reuse locked stats helper)
    comp = aim3_clinical_model_comparison(cons.rename(columns={}))
    comp.to_csv(REPORTS_DIR / "aim3_llm_model_comparison.csv", index=False)

    # 3. Inter-judge agreement per dimension: pairwise Spearman, Kendall's W, within-1 agreement
    agg_rows = []
    judges = sorted(raw.judge_id.unique())
    for d in DIMS:
        wide = raw.pivot_table(index=["page_id", "model_id"], columns="judge_id", values=d, aggfunc="first").dropna()
        n = len(wide)
        # pairwise Spearman
        rhos = [stats.spearmanr(wide[a], wide[b]).correlation for a, b in combinations(judges, 2)]
        mean_rho = float(np.nanmean(rhos))
        # Kendall's W from Friedman chi-square (k raters, n items): W = chi2 / (n*(k-1))
        k = len(judges)
        try:
            chi2, _ = stats.friedmanchisquare(*[wide[j].values for j in judges])
            kendall_w = float(chi2 / (n * (k - 1)))
        except ValueError:
            kendall_w = float("nan")
        # within-1-point agreement: fraction of items where max-min judge score <= 1
        within1 = float(((wide.max(axis=1) - wide.min(axis=1)) <= 1).mean())
        agg_rows.append({"dimension": d, "n_items": n, "n_judges": k,
                         "mean_pairwise_spearman": round(mean_rho, 3),
                         "kendall_w": round(kendall_w, 3),
                         "within_1_point_agreement": round(within1, 3)})
    pd.DataFrame(agg_rows).to_csv(REPORTS_DIR / "aim3_llm_interjudge.csv", index=False)

    # 4. Self-preference: does each judge score its OWN model's rewrites higher than others'?
    sp_rows = []
    for jid in judges:
        sub = raw[raw.judge_id == jid]
        for d in DIMS:
            own = sub[sub.model_id == jid][d]
            other = sub[sub.model_id != jid][d]
            if len(own) and len(other):
                # Mann-Whitney (ordinal); report means + p
                try:
                    _, p = stats.mannwhitneyu(own, other, alternative="two-sided")
                except ValueError:
                    p = float("nan")
                sp_rows.append({"judge_id": jid, "dimension": d,
                                "own_model_mean": round(own.mean(), 3),
                                "other_models_mean": round(other.mean(), 3),
                                "delta_own_minus_other": round(own.mean() - other.mean(), 3),
                                "mannwhitney_p": round(float(p), 4)})
    pd.DataFrame(sp_rows).to_csv(REPORTS_DIR / "aim3_llm_self_preference.csv", index=False)

    # 5. Trade-off: Spearman(Δ FKGL, accuracy/completeness) per model on consensus (reuse helper)
    trade = aim3_tradeoff_correlations(deltas, cons, primary_score="fkgl")
    trade.to_csv(REPORTS_DIR / "aim3_llm_tradeoff.csv", index=False)

    log.info("Aim 3 LLM-panel stats written to %s", REPORTS_DIR)
    # Console summary
    print("\n=== Per-model consensus (mean) ===")
    print(cons.groupby("model_id")[DIMS].mean().round(2).to_string())
    print("\n=== Inter-judge agreement ===")
    print(pd.DataFrame(agg_rows).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
