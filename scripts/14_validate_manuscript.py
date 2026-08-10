#!/usr/bin/env python3
"""Validate every reported number in Dr Naeem's manuscript against the pipeline.

This is the guard against silently shipping a number that the data does not
support. Each claim in the manuscript is encoded below as an explicit expected
value with a tolerance, recomputed from the pipeline outputs, and compared.

Design choices that matter:

* Manuscript values are hard-coded here on purpose. They are the independent
  reference; reading them from our own reports would make the check circular and
  guarantee a pass.
* Tolerances reflect the precision the manuscript reports to. A value printed as
  "4.84" is checked to +/-0.005; "P = .06" to +/-0.005. Counts must match exactly.
* A FAIL is not automatically an error in the pipeline -- it may be an error in
  the manuscript. Both are findings. Nothing here silently "fixes" a mismatch.

Outputs reports/manuscript_validation.csv and exits non-zero if anything fails,
so it can gate a commit.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import REPORTS_DIR, SCORES_DIR  # noqa: E402

MODEL_LABEL = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact binomial CI. Handles the k=0 and k=n edges, where the beta quantile
    is undefined and the bound is degenerate."""
    lo = 0.0 if k == 0 else stats.beta.ppf(alpha / 2, k, n - k + 1)
    hi = 1.0 if k == n else stats.beta.ppf(1 - alpha / 2, k + 1, n - k)
    return float(lo), float(hi)


def _add(checks, section, quantity, expected, actual, tol, note=""):
    if expected is None or actual is None or pd.isna(actual):
        ok = False
    elif isinstance(expected, str):
        ok = str(actual) == expected
    else:
        ok = abs(float(actual) - float(expected)) <= tol
    checks.append({
        "section": section, "quantity": quantity,
        "manuscript": expected, "computed": actual,
        "tolerance": tol, "status": "PASS" if ok else "FAIL", "note": note,
    })


def main() -> int:
    checks: list[dict] = []

    originals = pd.read_csv(SCORES_DIR / "originals.csv")
    rewrites = pd.read_csv(SCORES_DIR / "rewrites.csv")
    desc = pd.read_csv(REPORTS_DIR / "aim1_descriptives_overall.csv").set_index("score")
    paired = pd.read_csv(REPORTS_DIR / "aim2_paired_tests.csv")
    across = pd.read_csv(REPORTS_DIR / "aim2_across_models.csv").set_index("score")
    by_model = pd.read_csv(REPORTS_DIR / "aim3_compiled_by_model.csv")
    pooled = pd.read_csv(REPORTS_DIR / "aim3_compiled_pooled.csv").set_index("condition")
    cov = pd.read_csv(REPORTS_DIR / "aim3_compiled_coverage.csv").set_index("condition")
    irr = pd.read_csv(REPORTS_DIR / "aim3_compiled_irr.csv")
    evl = pd.read_csv(REPORTS_DIR / "aim3_compiled_expert_vs_lay.csv").set_index("axis")
    pres = pd.read_csv(REPORTS_DIR / "aim3_compiled_presentation_effect.csv")
    trade = pd.read_csv(REPORTS_DIR / "aim3_compiled_tradeoff.csv").set_index("model_id")
    llm = pd.read_csv(REPORTS_DIR / "aim3_llm_descriptives.csv")

    # ---------------- Aim 1: Table 1 + text ----------------
    t1 = {  # formula: (mean, sd, median)
        "fkre": (50.66, 12.06, 53.97), "fkgl": (10.54, 2.45, 10.31),
        "gfi": (13.71, 2.61, 13.09), "smog": (13.13, 1.81, 12.72),
        "cli": (11.51, 1.93, 11.23), "ari": (11.41, 2.88, 10.98),
    }
    for f, (mu, sd, med) in t1.items():
        _add(checks, "Table 1", f"{f} mean", mu, desc.loc[f, "mean"], 0.005)
        _add(checks, "Table 1", f"{f} SD", sd, desc.loc[f, "sd"], 0.005)
        _add(checks, "Table 1", f"{f} median", med, desc.loc[f, "median"], 0.005)
    _add(checks, "Table 1", "N pages", 26, int(desc.loc["fkgl", "n"]), 0)

    meeting = int((originals.fkgl <= 6.0).sum())
    lo, hi = clopper_pearson(meeting, len(originals))
    _add(checks, "Aim 1", "pages meeting FKGL<=6", 0, meeting, 0)
    _add(checks, "Aim 1", "Clopper-Pearson upper CI (%)", 13.2, 100 * hi, 0.05)
    _add(checks, "Aim 1", "min FKGL (most readable)", 6.95, originals.fkgl.min(), 0.005)
    _add(checks, "Aim 1", "max FKGL (least readable)", 16.36, originals.fkgl.max(), 0.005)
    # The manuscript's "cleaned body length" comes from the cleaning step, recorded
    # in the manifest -- not from originals.csv. The two use different word
    # counters (src.clean.count_words vs textstat's lexicon_count), so they differ
    # on every page by 2-46 words. The manifest is the correct source here; the
    # divergence is checked explicitly below so it stays visible.
    manifest = pd.read_csv(REPO_ROOT / "data" / "manifest.csv")
    inc = manifest[manifest.include == "Y"]
    _add(checks, "Aim 1", "mean cleaned words (manifest)", 872, inc.word_count_cleaned.mean(), 0.5)
    _add(checks, "Aim 1", "min cleaned words (manifest)", 252, inc.word_count_cleaned.min(), 0)
    _add(checks, "Aim 1", "max cleaned words (manifest)", 3153, inc.word_count_cleaned.max(), 0)
    _add(checks, "Aim 1", "manifest vs scorer word-count gap is known/bounded", True,
         bool((inc.word_count_cleaned.mean() - originals.word_count.mean()) < 25), 0,
         "two different word counters; manifest is the manuscript's source")

    proc = pd.read_csv(REPORTS_DIR / "aim1_inference_by_procedure.csv").set_index("score")
    site = pd.read_csv(REPORTS_DIR / "aim1_inference_by_site.csv").set_index("score")
    _add(checks, "Aim 1", "FKGL by-procedure P (ANOVA)", 0.94, proc.loc["fkgl", "p"], 0.005)
    _add(checks, "Aim 1", "FKGL by-site P (Kruskal)", 0.074, site.loc["fkgl", "p"], 0.0005)

    orig = originals.copy()
    orig["procedure"] = orig.page_id.str.split("__").str[1]
    for p, (mu, sd, n) in {"tavr": (10.7, 3.1, 10), "cta": (10.6, 2.3, 10),
                           "laao": (10.2, 1.9, 6)}.items():
        g = orig[orig.procedure == p]
        _add(checks, "Aim 1", f"{p} n pages", n, len(g), 0)
        _add(checks, "Aim 1", f"{p} mean FKGL", mu, g.fkgl.mean(), 0.05)
        _add(checks, "Aim 1", f"{p} SD FKGL", sd, g.fkgl.std(ddof=1), 0.05)

    # ---------------- Aim 2: Table 2 + text ----------------
    t2 = {  # (formula, model): (delta, ci_low, ci_high)
        ("fkre", "claude"): (28.74, 24.90, 32.59), ("fkre", "gemini"): (31.23, 27.20, 35.26),
        ("fkre", "openai"): (18.74, 15.34, 22.14),
        ("fkgl", "claude"): (-5.52, -6.32, -4.71), ("fkgl", "gemini"): (-5.74, -6.60, -4.88),
        ("fkgl", "openai"): (-3.90, -4.64, -3.17),
        ("gfi", "claude"): (-6.09, -6.99, -5.19), ("gfi", "gemini"): (-6.65, -7.59, -5.72),
        ("gfi", "openai"): (-4.35, -5.16, -3.55),
        ("smog", "claude"): (-4.43, -5.11, -3.76), ("smog", "gemini"): (-4.92, -5.57, -4.26),
        ("smog", "openai"): (-3.11, -3.71, -2.51),
        ("cli", "claude"): (-4.70, -5.28, -4.12), ("cli", "gemini"): (-4.92, -5.57, -4.27),
        ("cli", "openai"): (-2.91, -3.44, -2.39),
        ("ari", "claude"): (-6.15, -7.05, -5.25), ("ari", "gemini"): (-6.16, -7.16, -5.17),
        ("ari", "openai"): (-4.42, -5.29, -3.56),
    }
    pidx = paired.set_index(["score", "model_id"])
    for (f, m), (d, lo_, hi_) in t2.items():
        r = pidx.loc[(f, m)]
        _add(checks, "Table 2", f"{f}/{m} delta", d, r.mean_delta, 0.005)
        _add(checks, "Table 2", f"{f}/{m} CI low", lo_, r.ci_low, 0.005)
        _add(checks, "Table 2", f"{f}/{m} CI high", hi_, r.ci_high, 0.005)
        _add(checks, "Table 2", f"{f}/{m} Holm P<.001", True, bool(r.p_holm < 0.001), 0)
    for f, chi in {"fkre": 39.9, "fkgl": 38.0, "gfi": 39.1,
                   "smog": 40.9, "cli": 38.0, "ari": 34.6}.items():
        _add(checks, "Table 2", f"{f} Friedman chi2", chi, across.loc[f, "statistic"], 0.05)
    _add(checks, "Table 2", "Friedman n pages", 25, int(across.loc["fkgl", "n_pages"]), 0)
    _add(checks, "Aim 2", "FKGL Friedman P", 5.6e-9, across.loc["fkgl", "p"], 0.1e-9)

    for m, (dz, post, met, ntot) in {
        "claude": (-2.77, 5.02, 22, 26), "gemini": (-2.70, 4.80, 20, 26),
        "openai": (-2.18, 6.68, 9, 25),
    }.items():
        _add(checks, "Aim 2", f"{m} Cohen dz", dz, pidx.loc[("fkgl", m), "effect_size"], 0.005)
        sub = rewrites[rewrites.model_id == m]
        _add(checks, "Aim 2", f"{m} post-rewrite mean FKGL", post, sub.fkgl.mean(), 0.005)
        _add(checks, "Aim 2", f"{m} rewrites meeting FKGL<=6", met, int((sub.fkgl <= 6.0).sum()), 0)
        _add(checks, "Aim 2", f"{m} n rewrites", ntot, len(sub), 0)

    # ---------------- Aim 3 primary: Table 3 + text ----------------
    bm = by_model[by_model.condition == "expert_labeled"].set_index("model_id")
    t3 = {"claude": (51, 4.82, 0.39, 4.94, 0.24, 1.10, 0.36),
          "openai": (49, 4.84, 0.62, 4.84, 0.62, 1.10, 0.47),
          "gemini": (55, 4.85, 0.36, 4.64, 0.87, 1.07, 0.26)}
    for m, (n, am, asd, cm, csd, em, esd) in t3.items():
        r = bm.loc[m]
        _add(checks, "Table 3", f"{m} n ratings", n, int(r.n), 0)
        _add(checks, "Table 3", f"{m} accuracy mean", am, r.accuracy_1_5_mean, 0.005)
        _add(checks, "Table 3", f"{m} accuracy SD", asd, r.accuracy_1_5_sd, 0.005)
        _add(checks, "Table 3", f"{m} completeness mean", cm, r.completeness_1_5_mean, 0.005)
        _add(checks, "Table 3", f"{m} completeness SD", csd, r.completeness_1_5_sd, 0.005)
        _add(checks, "Table 3", f"{m} added-errors mean", em, r.added_errors_1_5_mean, 0.005)
        _add(checks, "Table 3", f"{m} added-errors SD", esd, r.added_errors_1_5_sd, 0.005)

    el = pooled.loc["expert_labeled"]
    _add(checks, "Aim 3", "expert reviewers", 6, int(cov.loc["expert_labeled", "reviewers"]), 0)
    _add(checks, "Aim 3", "expert ratings", 155, int(el.ratings), 0)
    _add(checks, "Aim 3", "expert rewrites covered", 77,
         int(cov.loc["expert_labeled", "rewrites_covered"]), 0)
    _add(checks, "Aim 3", "expert pooled accuracy", 4.84, el.accuracy_mean, 0.005)
    _add(checks, "Aim 3", "% accuracy >=4", 99.4, el.pct_accuracy_ge4, 0.05)
    _add(checks, "Aim 3", "% accuracy =5", 85.8, el.pct_accuracy_eq5, 0.05)
    _add(checks, "Aim 3", "% added-errors <=2", 98.7, el.pct_added_le2, 0.05)
    _add(checks, "Aim 3", "n ratings accuracy <=3", 1, int(el.n_accuracy_le3), 0)
    _add(checks, "Aim 3", "n ratings added-errors >=3", 2, int(el.n_added_ge3), 0)

    ei = irr[irr.condition == "expert_labeled"].set_index("axis")
    _add(checks, "Aim 3", "expert rater-pairs", 104, int(ei.loc["accuracy_1_5", "rater_pairs"]), 0)
    for ax, ex, ac1, kap in [("accuracy_1_5", 82, 0.77, 0.06),
                             ("completeness_1_5", 75, 0.79, 0.12),
                             ("added_errors_1_5", 88, 0.89, -0.03)]:
        _add(checks, "Aim 3", f"{ax} exact agreement %", ex, ei.loc[ax, "pct_exact"], 0.5)
        _add(checks, "Aim 3", f"{ax} within-1 >=95%", True,
             bool(ei.loc[ax, "pct_within_1"] >= 95), 0)
        _add(checks, "Aim 3", f"{ax} Gwet AC1", ac1, ei.loc[ax, "gwet_ac1"], 0.01,
             "manuscript reports AC1 to 2dp (truncated)")
        _add(checks, "Aim 3", f"{ax} quad-weighted kappa", kap, ei.loc[ax, "quad_weighted_kappa"], 0.005)

    for m, (rho, p) in {"gemini": (-0.37, 0.06), "claude": (0.25, 0.22),
                        "openai": (0.03, 0.90)}.items():
        _add(checks, "Aim 3", f"{m} Spearman rho (reduction vs accuracy)", rho,
             trade.loc[m, "spearman_rho_reduction_vs_accuracy"], 0.005)
        _add(checks, "Aim 3", f"{m} Spearman P", p, trade.loc[m, "p_value"], 0.005)

    # ---------------- Aim 3 secondary: lay arm and presentation ----------------
    _add(checks, "Lay arm", "lay ratings (pooled)", 385, int(pooled.loc["layperson_all", "ratings"]), 0)
    _add(checks, "Lay arm", "lay readers (neutral)", 3,
         int(cov.loc["layperson_neutral", "reviewers"]), 0)
    _add(checks, "Lay arm", "lay readers (labeled)", 2,
         int(cov.loc["layperson_labeled", "reviewers"]), 0)
    for ax, lay_m, exp_m, p in [("accuracy_1_5", 4.94, 4.84, 0.001),
                                ("completeness_1_5", 4.90, 4.80, 0.20),
                                ("added_errors_1_5", 1.08, 1.09, 0.95)]:
        _add(checks, "Lay arm", f"{ax} lay mean", lay_m, evl.loc[ax, "layperson_mean"], 0.005)
        _add(checks, "Lay arm", f"{ax} expert mean", exp_m, evl.loc[ax, "expert_mean"], 0.005)
        _add(checks, "Lay arm", f"{ax} lay-vs-expert P", p, evl.loc[ax, "mannwhitney_p"], 0.01)

    po = pres[pres.scope == "overall"].set_index("axis")
    for ax, lab, neu in [("accuracy_1_5", 4.99, 4.90), ("completeness_1_5", 4.98, 4.84),
                         ("added_errors_1_5", 1.00, 1.14)]:
        _add(checks, "Presentation", f"{ax} lay labeled mean", lab, po.loc[ax, "labeled_mean"], 0.005)
        _add(checks, "Presentation", f"{ax} lay neutral mean", neu, po.loc[ax, "neutral_mean"], 0.005)
        _add(checks, "Presentation", f"{ax} P <= .001", True,
             bool(po.loc[ax, "mannwhitney_p"] <= 0.001 + 1e-9), 0)

    # ---------------- Aim 3 secondary: Table 4, automated judges ----------------
    # aim3_llm_descriptives.csv is long-format: one row per (model_id, dimension).
    ld = llm.set_index(["model_id", "dimension"])
    t4 = {"openai": (25, 4.998, 0.00, 4.95, 0.16, 1.07, 0.17),
          "claude": (26, 4.91, 0.18, 4.91, 0.20, 1.18, 0.36),
          "gemini": (26, 4.69, 0.44, 4.81, 0.29, 1.45, 0.70)}
    for m, (n, am, asd, cm, csd, em, esd) in t4.items():
        for dim, mu, sd in [("accuracy_1_5", am, asd),
                            ("completeness_1_5", cm, csd),
                            ("added_errors_1_5", em, esd)]:
            key = (m, dim)
            if key not in ld.index:
                _add(checks, "Table 4", f"{m} {dim}", mu, None, 0.005, "row missing")
                continue
            r = ld.loc[key]
            _add(checks, "Table 4", f"{m} {dim} n", n, int(r["n"]), 0)
            _add(checks, "Table 4", f"{m} {dim} mean", mu, r["mean"], 0.006)
            _add(checks, "Table 4", f"{m} {dim} SD", sd, r["sd"], 0.006)

    # ---------------- report ----------------
    out = pd.DataFrame(checks)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(REPORTS_DIR / "manuscript_validation.csv", index=False)

    n_pass = int((out.status == "PASS").sum())
    n_fail = int((out.status == "FAIL").sum())

    print("=" * 96)
    print("MANUSCRIPT VALIDATION  —  Naeem_final_clean_cardiac_CT_readability.docx")
    print("=" * 96)
    for sec in out.section.unique():
        s = out[out.section == sec]
        print(f"  {sec:<14s} {int((s.status=='PASS').sum()):3d} pass  "
              f"{int((s.status=='FAIL').sum()):3d} fail   ({len(s)} checks)")
    print("-" * 96)
    print(f"  TOTAL: {n_pass} passed, {n_fail} failed, {len(out)} checks")

    if n_fail:
        print("\nFAILURES (manuscript value vs computed):")
        for _, r in out[out.status == "FAIL"].iterrows():
            note = f"  [{r['note']}]" if r["note"] else ""
            print(f"  - {r['section']:<13s} {r['quantity']:<46s} "
                  f"manuscript={r['manuscript']}  computed={r['computed']}{note}")
    print(f"\nWrote {REPORTS_DIR / 'manuscript_validation.csv'}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
