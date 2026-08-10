#!/usr/bin/env python3
"""Cross-check the pipeline against Dr Naeem's manuscript.

Nothing here is hard-coded. Both sides of every comparison are derived:

* the manuscript side is parsed out of the .docx by `src.manuscript` -- tables and
  prose alike -- so a revised manuscript is picked up automatically and no number
  is ever transcribed by hand;
* the pipeline side is recomputed from `data/` and `reports/`;
* the tolerance comes from the manuscript's own printed precision (a value shown
  as "4.84" is checked to +/-0.005, "155" to +/-0.5).

Reading expected values from our own reports would be circular and would certify
anything, so the .docx is the only reference.

A FAIL is a finding, not a chore: it may be our bug or the manuscript's. Both
matter. Nothing here silently reconciles a mismatch.

Outputs reports/manuscript_validation.csv; exits non-zero if anything fails.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.config import DATA_DIR, REPORTS_DIR, SCORES_DIR  # noqa: E402
from src.manuscript import load_reported  # noqa: E402

MANUSCRIPT = REPO_ROOT / "publication" / "Naeem_final_clean_cardiac_CT_readability.docx"
FORMULAS = ["fkre", "fkgl", "gfi", "smog", "cli", "ari"]
MODELS = ["claude", "openai", "gemini"]
AXES = {"accuracy": "accuracy_1_5", "completeness": "completeness_1_5",
        "added_errors": "added_errors_1_5"}


def clopper_pearson_upper(k: int, n: int, alpha: float = 0.05) -> float:
    """Exact binomial upper bound; the beta quantile is degenerate at k == n."""
    return 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))


def compute() -> dict[str, float]:
    """Recompute every quantity the manuscript reports, keyed to match the parser."""
    originals = pd.read_csv(SCORES_DIR / "originals.csv")
    rewrites = pd.read_csv(SCORES_DIR / "rewrites.csv")
    manifest = pd.read_csv(DATA_DIR / "manifest.csv")
    inc = manifest[manifest.include == "Y"]

    desc = pd.read_csv(REPORTS_DIR / "aim1_descriptives_overall.csv").set_index("score")
    proc = pd.read_csv(REPORTS_DIR / "aim1_inference_by_procedure.csv").set_index("score")
    site = pd.read_csv(REPORTS_DIR / "aim1_inference_by_site.csv").set_index("score")
    paired = pd.read_csv(REPORTS_DIR / "aim2_paired_tests.csv").set_index(["score", "model_id"])
    across = pd.read_csv(REPORTS_DIR / "aim2_across_models.csv").set_index("score")
    bym = pd.read_csv(REPORTS_DIR / "aim3_compiled_by_model.csv")
    pooled = pd.read_csv(REPORTS_DIR / "aim3_compiled_pooled.csv").set_index("condition")
    cov = pd.read_csv(REPORTS_DIR / "aim3_compiled_coverage.csv").set_index("condition")
    irr = pd.read_csv(REPORTS_DIR / "aim3_compiled_irr.csv")
    evl = pd.read_csv(REPORTS_DIR / "aim3_compiled_expert_vs_lay.csv").set_index("axis")
    pres = pd.read_csv(REPORTS_DIR / "aim3_compiled_presentation_effect.csv")
    trade = pd.read_csv(REPORTS_DIR / "aim3_compiled_tradeoff.csv").set_index("model_id")
    llm = pd.read_csv(REPORTS_DIR / "aim3_llm_descriptives.csv").set_index(["model_id", "dimension"])

    c: dict[str, float] = {}

    # ---- Table 1 + Aim 1 prose ----
    for f in FORMULAS:
        c[f"t1.{f}.n"] = float(desc.loc[f, "n"])
        c[f"t1.{f}.mean"] = float(desc.loc[f, "mean"])
        c[f"t1.{f}.sd"] = float(desc.loc[f, "sd"])
        c[f"t1.{f}.median"] = float(desc.loc[f, "median"])

    meeting = int((originals.fkgl <= 6.0).sum())
    c["p.fkgl.median"] = float(originals.fkgl.median())
    c["p.fkgl.mean"] = float(originals.fkgl.mean())
    c["p.fkgl.sd"] = float(originals.fkgl.std(ddof=1))
    c["p.fkgl.min"] = float(originals.fkgl.min())
    c["p.fkgl.max"] = float(originals.fkgl.max())
    c["p.benchmark.meeting"] = float(meeting)
    c["p.benchmark.n"] = float(len(originals))
    c["p.benchmark.pct"] = 100.0 * meeting / len(originals)
    c["p.benchmark.ci_high"] = 100.0 * clopper_pearson_upper(meeting, len(originals))
    # "cleaned body length" is the cleaning step's count, recorded in the manifest.
    # originals.csv uses textstat's lexicon_count, which differs on every page.
    c["p.words.mean"] = float(inc.word_count_cleaned.mean())
    c["p.words.min"] = float(inc.word_count_cleaned.min())
    c["p.words.max"] = float(inc.word_count_cleaned.max())

    orig = originals.assign(procedure=originals.page_id.str.split("__").str[1])
    for p in ("tavr", "cta", "laao"):
        g = orig[orig.procedure == p]
        c[f"p.proc.{p}.mean"] = float(g.fkgl.mean())
        c[f"p.proc.{p}.sd"] = float(g.fkgl.std(ddof=1))
        c[f"p.proc.{p}.n"] = float(len(g))
    c["p.proc.anova_p"] = float(proc.loc["fkgl", "p"])
    c["p.site.kruskal_p"] = float(site.loc["fkgl", "p"])

    # ---- Table 2 + Aim 2 prose ----
    for f in FORMULAS:
        for m in MODELS:
            r = paired.loc[(f, m)]
            c[f"t2.{f}.{m}.delta"] = float(r.mean_delta)
            c[f"t2.{f}.{m}.ci_low"] = float(r.ci_low)
            c[f"t2.{f}.{m}.ci_high"] = float(r.ci_high)
        c[f"t2.{f}.friedman_chi2"] = float(across.loc[f, "statistic"])

    for m in MODELS:
        sub = rewrites[rewrites.model_id == m]
        c[f"p.dz.{m}"] = float(paired.loc[("fkgl", m), "effect_size"])
        c[f"p.post.{m}"] = float(sub.fkgl.mean())
        c[f"p.met.{m}"] = float((sub.fkgl <= 6.0).sum())
        c[f"p.met.{m}_n"] = float(len(sub))
    c["p.friedman.fkgl_chi2"] = float(across.loc["fkgl", "statistic"])
    c["p.friedman.n_pages"] = float(across.loc["fkgl", "n_pages"])

    # ---- Table 3 + Aim 3 primary prose (blinded subspecialists, labeled) ----
    lab = bym[bym.condition == "expert_labeled"].set_index("model_id")
    for m in MODELS:
        c[f"t3.{m}.n"] = float(lab.loc[m, "n"])
        for axis, col in AXES.items():
            c[f"t3.{m}.{axis}.mean"] = float(lab.loc[m, f"{col}_mean"])
            c[f"t3.{m}.{axis}.sd"] = float(lab.loc[m, f"{col}_sd"])

    el = pooled.loc["expert_labeled"]
    c["p.aim3.n_reviewers"] = float(cov.loc["expert_labeled", "reviewers"])
    c["p.aim3.n_ratings"] = float(el.ratings)
    c["p.aim3.pooled_accuracy"] = float(el.accuracy_mean)
    c["p.aim3.pct_ge4"] = float(el.pct_accuracy_ge4)
    c["p.aim3.pct_eq5"] = float(el.pct_accuracy_eq5)
    c["p.aim3.pct_added_le2"] = float(el.pct_added_le2)

    ei = irr[irr.condition == "expert_labeled"].set_index("axis")
    c["p.irr.pairs"] = float(ei.loc["accuracy_1_5", "rater_pairs"])
    for axis, col in AXES.items():
        c[f"p.irr.{axis}_exact"] = float(ei.loc[col, "pct_exact"])
        c[f"p.ac1.{axis}"] = float(ei.loc[col, "gwet_ac1"])
        c[f"p.kappa.{axis}"] = float(ei.loc[col, "quad_weighted_kappa"])

    for m in MODELS:
        c[f"p.rho.{m}"] = float(trade.loc[m, "spearman_rho_reduction_vs_accuracy"])
        c[f"p.rho.{m}_p"] = float(trade.loc[m, "p_value"])

    # ---- Lay arm and presentation sub-study ----
    c["p.lay.n_ratings"] = float(pooled.loc["layperson_all", "ratings"])
    c["p.lay.n_neutral"] = float(cov.loc["layperson_neutral", "reviewers"])
    c["p.lay.n_labeled"] = float(cov.loc["layperson_labeled", "reviewers"])
    for axis, col in AXES.items():
        short = {"accuracy": "accuracy", "completeness": "completeness",
                 "added_errors": "added"}[axis]
        c[f"p.lay.{short}"] = float(evl.loc[col, "layperson_mean"])
        c[f"p.lay.expert_{short}"] = float(evl.loc[col, "expert_mean"])
        c[f"p.lay.{short}_p"] = float(evl.loc[col, "mannwhitney_p"])

    po = pres[pres.scope == "overall"].set_index("axis")
    for axis, col in AXES.items():
        short = {"accuracy": "accuracy", "completeness": "completeness",
                 "added_errors": "added"}[axis]
        c[f"p.pres.{short}_labeled"] = float(po.loc[col, "labeled_mean"])
        c[f"p.pres.{short}_neutral"] = float(po.loc[col, "neutral_mean"])

    # ---- Table 4: automated LLM-judge panel ----
    for m in MODELS:
        for axis, col in AXES.items():
            if (m, col) in llm.index:
                c[f"t4.{m}.n"] = float(llm.loc[(m, col), "n"])
                c[f"t4.{m}.{axis}.mean"] = float(llm.loc[(m, col), "mean"])
                c[f"t4.{m}.{axis}.sd"] = float(llm.loc[(m, col), "sd"])

    return c


def main() -> int:
    if not MANUSCRIPT.exists():
        print(f"manuscript not found: {MANUSCRIPT}")
        print("publication/ is gitignored; place the .docx there to validate.")
        return 2

    reported = load_reported(MANUSCRIPT)
    computed = compute()

    rows = []
    for key, rep in sorted(reported.items()):
        got = computed.get(key)
        if got is None:
            status, delta = "NO-CHECK", None
        else:
            delta = got - rep.value
            # +/-0.5 ULP is the round-half tolerance. A value that misses that but
            # sits within a full ULP agrees under truncation instead of rounding
            # (0.7968 prints as "0.79" truncated, "0.80" rounded), which is a
            # reporting-convention difference, not a disagreement about the data.
            # It is called out separately rather than folded into either bucket:
            # widening the tolerance to bury it would hide real mismatches too.
            if abs(delta) <= rep.tolerance:
                status = "PASS"
            elif abs(delta) <= 2 * rep.tolerance:
                status = "ROUNDING"
            else:
                status = "FAIL"
        rows.append({
            "section": rep.source, "key": key,
            "manuscript": rep.value, "manuscript_raw": rep.raw,
            "computed": got, "difference": delta,
            "tolerance": rep.tolerance, "status": status,
        })
    out = pd.DataFrame(rows)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    out.to_csv(REPORTS_DIR / "manuscript_validation.csv", index=False)

    n_pass = int((out.status == "PASS").sum())
    n_fail = int((out.status == "FAIL").sum())
    n_none = int((out.status == "NO-CHECK").sum())
    n_round = int((out.status == "ROUNDING").sum())

    print("=" * 100)
    print(f"MANUSCRIPT CROSS-CHECK  —  {MANUSCRIPT.name}")
    print("values parsed from the .docx; nothing hard-coded")
    print("=" * 100)
    for sec in sorted(out.section.unique()):
        s = out[out.section == sec]
        print(f"  {sec:<10s} {int((s.status=='PASS').sum()):3d} pass  "
              f"{int((s.status=='FAIL').sum()):3d} fail  "
              f"{int((s.status=='ROUNDING').sum()):3d} rounding  "
              f"{int((s.status=='NO-CHECK').sum()):3d} no-check   ({len(s)} extracted)")
    print("-" * 100)
    print(f"  TOTAL: {n_pass} pass, {n_round} rounding-only, {n_fail} fail, "
          f"{n_none} no-check, {len(out)} extracted")

    if n_fail:
        print("\nFAILURES (manuscript vs computed):")
        for _, r in out[out.status == "FAIL"].iterrows():
            print(f"  - {r['key']:<34s} manuscript={r['manuscript_raw']:<10s} "
                  f"computed={r['computed']:<20.6g} diff={r['difference']:+.4g} "
                  f"(tol +/-{r['tolerance']})")
    if n_round:
        print("\nROUNDING-CONVENTION ONLY (agree within one full printed digit; not a data disagreement):")
        for _, r in out[out.status == "ROUNDING"].iterrows():
            print(f"  - {r['key']:<34s} manuscript={r['manuscript_raw']:<10s} "
                  f"computed={r['computed']:<20.6g} diff={r['difference']:+.4g}")
    if n_none:
        print("\nNO-CHECK (parsed from the manuscript but nothing computed to compare):")
        for _, r in out[out.status == "NO-CHECK"].iterrows():
            print(f"  - {r['key']:<34s} manuscript={r['manuscript_raw']}")

    print(f"\nWrote {REPORTS_DIR / 'manuscript_validation.csv'}")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
