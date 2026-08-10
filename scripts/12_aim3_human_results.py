"""Aim 3 — compile the human-review results (interim).

Reads every returned reviewer sheet under data/review/reviewer_responses/ and
separates the THREE conditions that were actually collected (the filename encodes
all three signals):

  * expert_labeled  — subspecialist reviewers, standard instrument that labels the
                      panels "Original page" / "AI rewrite". This is the Aim 3
                      PRIMARY endpoint.
  * expert_neutral  — subspecialist reviewers, neutral-presentation instrument
                      ("reference passage" / "passage to score"). A parallel
                      presentation-bias cohort (files carry a `neutral` tag).
  * layperson       — non-clinician reviewers, standard instrument.

It is deliberately variant-aware so the neutral sheets are NOT pooled with the
labeled ones (a naive glob would silently merge them). Re-runnable
and idempotent; reads only committed inputs. This is an INTERIM compilation
(one labeled expert for set C is still pending) and does not replace the locked
final analysis in 07_run_statistics.py.

Writes reports/aim3_compiled_*.csv (run scripts/13 for the figures).
"""

from __future__ import annotations

import re
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.agreement import (  # noqa: E402
    RATING_CATEGORIES,
    gwet_ac1,
    mean_pairwise_weighted_kappa,
)
from src.config import REPORTS_DIR, REVIEW_DIR, SCORES_DIR  # noqa: E402
from src.stats import pairwise_posthoc_models, spearman_bootstrap_ci  # noqa: E402

SCORES_ROOT = REVIEW_DIR / "reviewer_responses"
AXES = ["accuracy_1_5", "completeness_1_5", "added_errors_1_5"]
MODEL_ORDER = ["claude", "openai", "gemini"]
MODEL_LABEL = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}


# Four cohorts, because presentation and reviewer type vary independently.
# Collapsing the two lay cohorts would pool the labeled and neutral instruments
# into one mean, which is exactly the confound the study is designed to measure.
CONDITIONS = ["expert_labeled", "expert_neutral", "layperson_labeled", "layperson_neutral"]
CONDITION_LABEL = {
    "expert_labeled": "Subspecialist, standard instrument (primary)",
    "expert_neutral": "Subspecialist, neutral presentation",
    "layperson_labeled": "Layperson, standard (labeled) instrument",
    "layperson_neutral": "Layperson, neutral presentation",
}
# The manuscript reports lay readers pooled across both presentations (385
# ratings from 5 readers) when contrasting them with the subspecialists.
LAY_CONDITIONS = ["layperson_labeled", "layperson_neutral"]

# Reviewer identity is taken from the file NAME slug. Sheets are keyed by opaque
# participant IDs (E01-E06 subspecialists, L01-L05 lay readers); the name-to-ID
# crosswalk lives outside version control. Historically the free-text
# `reviewer_name` column was inconsistent across returns, which is why the slug --
# not that column -- is the canonical id for counting reviewers and pairing raters.
_SLUG_RE = re.compile(r"^aim3_scores_(?:neutral_)?set_[a-c]_(.+?)_(?:expert|layman|layperson)$")


def _reviewer_id(stem: str) -> str:
    m = _SLUG_RE.match(stem.lower())
    return m.group(1) if m else stem.lower()


def load() -> pd.DataFrame:
    frames = []
    for f in sorted(SCORES_ROOT.rglob("aim3_scores_*.csv")):
        d = pd.read_csv(f)
        s = f.stem.lower()
        d["reviewer_type"] = "layperson" if ("layman" in s or "layperson" in s) else "expert"
        d["presentation"] = "neutral" if "neutral" in s else "standard"
        d["reviewer_id"] = _reviewer_id(f.stem)
        d["source_file"] = f.name
        frames.append(d)
    if not frames:
        raise SystemExit(f"no score sheets under {SCORES_ROOT}")
    df = pd.concat(frames, ignore_index=True)
    df = df.merge(pd.read_csv(REVIEW_DIR / "unblinding_key.csv"), on="blind_id", how="left", validate="many_to_one")
    df["procedure"] = df["page_id"].str.split("__").str[1]
    for c in AXES:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["condition"] = np.where(
        df.reviewer_type == "layperson",
        np.where(df.presentation == "neutral", "layperson_neutral", "layperson_labeled"),
        np.where(df.presentation == "neutral", "expert_neutral", "expert_labeled"),
    )
    df["reviewer_display"] = df["reviewer_id"].str.replace("_", " ").str.title()
    return df


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    # Derived from the blinding key rather than written in: the total is a
    # property of the study design, and a literal here would silently go stale if
    # the rewrite set ever changed.
    n_rewrites_total = pd.read_csv(REVIEW_DIR / "unblinding_key.csv").blind_id.nunique()
    rows = []
    for c in CONDITIONS:
        g = df[df.condition == c]
        rows.append({
            "condition": c,
            "condition_label": CONDITION_LABEL[c],
            "reviewers": g.reviewer_id.nunique(),
            "ratings": len(g),
            "rewrites_covered": g.blind_id.nunique(),
            "rewrites_total": n_rewrites_total,
            "mean_raters_per_rewrite": round(len(g) / max(g.blind_id.nunique(), 1), 2),
            "sets": ", ".join(sorted(g.set_id.astype(str).unique())),
        })
    return pd.DataFrame(rows)


def reviewers(df: pd.DataFrame) -> pd.DataFrame:
    g = (df.groupby(["condition", "reviewer_id", "reviewer_display"])
           .agg(ratings=("blind_id", "size"),
                sets=("set_id", lambda s: ", ".join(sorted(s.astype(str).unique()))))
           .reset_index()
           .sort_values(["condition", "reviewer_id"]))
    return g


def expert_rewrite_means(df: pd.DataFrame) -> pd.DataFrame:
    """One expert mean per rewrite -- the PRIMARY Aim 3 unit of analysis.

    A rewrite scored by three subspecialists is one clinical observation, not three.
    Averaging first stops multiply-scored rewrites carrying extra weight in the model
    descriptives, the model comparison and the trade-off correlations. Expect 77 rows:
    26 Claude + 25 GPT-5.5 + 26 Gemini.

    The 155 raw ratings remain the right unit for reviewer coverage, rating-level
    percentages and interrater agreement, which are about rating events.
    """
    lab = df[df.condition == "expert_labeled"]
    return (lab.groupby(["page_id", "model_id"], as_index=False)[AXES]
               .mean()
               .sort_values(["page_id", "model_id"])
               .reset_index(drop=True))


def _condition_groups(df: pd.DataFrame) -> list[tuple[str, pd.DataFrame]]:
    """The four cohorts, plus lay readers pooled across both presentations.

    `layperson_all` is the 385-rating pooled lay cohort the manuscript contrasts
    with the subspecialists. It is reported as an extra row, never as a
    replacement for the two lay cohorts, so the presentation split stays visible.
    """
    groups = [(c, df[df.condition == c]) for c in CONDITIONS]
    groups.append(("layperson_all", df[df.condition.isin(LAY_CONDITIONS)]))
    return groups


def by_model(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c, sub in _condition_groups(df):
        for m in MODEL_ORDER:
            g = sub[sub.model_id == m]
            r = {"condition": c, "model_id": m, "model": MODEL_LABEL[m], "n": len(g)}
            for ax in AXES:
                r[f"{ax}_mean"] = g[ax].mean()
                r[f"{ax}_sd"] = g[ax].std(ddof=1)
            r["pct_accuracy_max"] = 100 * (g.accuracy_1_5 == 5).mean()
            rows.append(r)
    return pd.DataFrame(rows)


def by_model_primary(rw: pd.DataFrame) -> pd.DataFrame:
    """PRIMARY per-model clinical summary, one row per rewrite (not per rating)."""
    rows = []
    for m in MODEL_ORDER:
        g = rw[rw.model_id == m]
        r = {"model_id": m, "model": MODEL_LABEL[m], "n_rewrites": len(g)}
        for ax in AXES:
            r[f"{ax}_mean"] = g[ax].mean()
            r[f"{ax}_sd"] = g[ax].std(ddof=1)
        rows.append(r)
    return pd.DataFrame(rows)


def pooled(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c, g in _condition_groups(df):
        rows.append({
            "condition": c, "ratings": len(g),
            "accuracy_mean": g.accuracy_1_5.mean(), "completeness_mean": g.completeness_1_5.mean(),
            "added_errors_mean": g.added_errors_1_5.mean(),
            "pct_accuracy_ge4": 100 * (g.accuracy_1_5 >= 4).mean(),
            "pct_accuracy_eq5": 100 * (g.accuracy_1_5 == 5).mean(),
            "pct_added_le2": 100 * (g.added_errors_1_5 <= 2).mean(),
            "n_accuracy_le3": int((g.accuracy_1_5 <= 3).sum()),
            "n_added_ge3": int((g.added_errors_1_5 >= 3).sum()),
        })
    return pd.DataFrame(rows)


def irr(df: pd.DataFrame) -> pd.DataFrame:
    """Agreement on multiply-scored rewrites, per condition and axis.

    Reports raw percent agreement alongside two chance-corrected coefficients.
    AC1 uses the protocol's 1-5 category set (see src/agreement.py) -- one
    canonical value, not a menu of conventions.
    Under this study's strong ceiling (~86% of expert accuracy ratings are 5),
    quadratic-weighted Cohen kappa collapses toward zero while agreement is in
    fact excellent; Gwet AC1 is reported because it is resistant to that paradox.
    Both are shown so the contrast is visible rather than hidden.
    """
    rows = []
    for c in CONDITIONS:
        g = df[df.condition == c]
        for ax in AXES:
            piv = g.pivot_table(index="blind_id", columns="reviewer_id", values=ax, aggfunc="first")
            ex, w1 = [], []
            for _, r in piv.iterrows():
                vals = r.dropna().values
                for a, b in combinations(vals, 2):
                    ex.append(a == b)
                    w1.append(abs(a - b) <= 1)
            rows.append({"condition": c, "axis": ax, "rater_pairs": len(ex),
                         "pct_exact": 100 * np.mean(ex) if ex else np.nan,
                         "pct_within_1": 100 * np.mean(w1) if w1 else np.nan,
                         # Default AC1 derives the category set from the data,
                         # matching Gwet's reference implementation (irrCAC) and
                         # the manuscript. The fixed-scale variant holds q at 5
                         # so cohorts stay comparable; under a ceiling the two
                         # diverge sharply, so both are reported.
                         "gwet_ac1": (
                             gwet_ac1(piv, RATING_CATEGORIES)
                             if len(piv.columns) > 1 else np.nan
                         ),
                         "quad_weighted_kappa": (
                             mean_pairwise_weighted_kappa(piv) if len(piv.columns) > 1 else np.nan
                         )})
    return pd.DataFrame(rows)


def _rewrite_means(df: pd.DataFrame, condition: str) -> pd.DataFrame:
    """Mean rating per rewrite within one cohort, so each rewrite counts once."""
    g = df[df.condition == condition]
    return g.groupby("blind_id", as_index=False)[AXES].mean()


def presentation_effect(df: pd.DataFrame) -> pd.DataFrame:
    """Labeled vs neutral presentation WITHIN the lay cohort, at the rewrite level.

    Both lay cohorts scored the same rewrites, and several readers scored each one,
    so raw ratings are repeated observations of the same unit. Averaging to one value
    per rewrite and pairing on blind_id gives a paired Wilcoxon over matched rewrites
    instead of a Mann-Whitney over pseudo-replicated ratings.

    Different readers scored each presentation, so reader identity is confounded with
    presentation. This is a descriptive presentation comparison, NOT evidence of an
    AI-labeling effect.
    """
    lab = _rewrite_means(df, "layperson_labeled").set_index("blind_id")
    neu = _rewrite_means(df, "layperson_neutral").set_index("blind_id")
    common = lab.index.intersection(neu.index)
    key = df[["blind_id", "model_id"]].drop_duplicates().set_index("blind_id")
    rows = []
    for scope in ["overall", *MODEL_ORDER]:
        ids = common if scope == "overall" else common.intersection(
            key[key.model_id == scope].index)
        for ax in AXES:
            a_, b_ = lab.loc[ids, ax], neu.loc[ids, ax]
            p = stats.wilcoxon(a_, b_)[1] if len(ids) >= 2 and (a_ - b_).abs().sum() > 0 else np.nan
            rows.append({"scope": scope, "axis": ax, "n_rewrites": len(ids),
                         "labeled_mean": a_.mean(), "neutral_mean": b_.mean(),
                         "mean_difference": (a_ - b_).mean(), "wilcoxon_p": p})
    return pd.DataFrame(rows)


def expert_vs_lay(df: pd.DataFrame) -> pd.DataFrame:
    """Subspecialists vs lay readers on the SAME (standard) instrument, per rewrite.

    Comparing expert_labeled with layperson_labeled holds the instrument constant, so
    the contrast is reader type rather than reader type confounded with presentation.
    Ratings are averaged to one value per rewrite and paired on blind_id, avoiding the
    pseudo-replication of testing 155 ratings against 385.

    The pooled 385-rating lay mean remains available in the pooled table as a
    descriptive summary only.
    """
    exp = _rewrite_means(df, "expert_labeled").set_index("blind_id")
    lay = _rewrite_means(df, "layperson_labeled").set_index("blind_id")
    common = exp.index.intersection(lay.index)
    rows = []
    for ax in AXES:
        a_, b_ = exp.loc[common, ax], lay.loc[common, ax]
        p = stats.wilcoxon(a_, b_)[1] if len(common) >= 2 and (a_ - b_).abs().sum() > 0 else np.nan
        rows.append({"axis": ax, "n_rewrites": len(common),
                     "expert_mean": a_.mean(), "layperson_mean": b_.mean(),
                     "mean_difference": (a_ - b_).mean(), "wilcoxon_p": p})
    return pd.DataFrame(rows)


def tradeoff(rw: pd.DataFrame) -> pd.DataFrame:
    """Spearman correlation of FKGL reduction with expert accuracy AND completeness.

    Reduction is defined once, positively (original - rewrite), so a larger value
    always means more grade levels removed. 95% CIs come from 5000 bootstrap
    resamples of rewrites with a fixed seed, as the analysis plan specifies.

    Added errors are deliberately excluded from the primary trade-off; they are
    reported elsewhere as descriptive.
    """
    deltas = pd.read_csv(SCORES_DIR / "deltas.csv")[["page_id", "model_id", "fkgl_delta"]]
    pm = rw.merge(deltas, on=["page_id", "model_id"])
    pm["fkgl_reduction"] = -pm["fkgl_delta"]
    rows = []
    for m in MODEL_ORDER:
        s_ = pm[pm.model_id == m]
        for ax in ("accuracy_1_5", "completeness_1_5"):
            res = spearman_bootstrap_ci(s_["fkgl_reduction"].to_numpy(), s_[ax].to_numpy())
            rows.append({"model_id": m, "model": MODEL_LABEL[m], "axis": ax,
                         "n_rewrites": res["n"], "spearman_rho": res["rho"],
                         "ci_low": res["ci_low"], "ci_high": res["ci_high"],
                         "p_value": res["p_value"], "n_boot_valid": res["n_boot_valid"]})
    return pd.DataFrame(rows)


def across_model(rw: pd.DataFrame) -> pd.DataFrame:
    """Friedman across models on rewrite-level expert means."""
    rows = []
    for ax in AXES:
        wide = rw.pivot_table(index="page_id", columns="model_id", values=ax).dropna(
            subset=MODEL_ORDER)
        if len(wide) >= 3:
            chi2, p = stats.friedmanchisquare(*[wide[m] for m in MODEL_ORDER])
            rows.append({"axis": ax, "n_pages": len(wide),
                         **{m: wide[m].mean() for m in MODEL_ORDER},
                         "friedman_chi2": chi2, "p_value": p})
    return pd.DataFrame(rows)


def across_model_posthoc(rw: pd.DataFrame, omnibus: pd.DataFrame) -> pd.DataFrame:
    """Paired Wilcoxon-Holm post-hoc, run only where the omnibus is significant."""
    out = []
    for _, r in omnibus.iterrows():
        if not (r.p_value < 0.05):
            continue
        wide = rw.pivot_table(index="page_id", columns=" model_id".strip(),
                              values=r.axis).dropna(subset=MODEL_ORDER)
        out.append(pairwise_posthoc_models(wide, MODEL_ORDER, label=r.axis))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(
        columns=["label", "model_a", "model_b", "n_pairs", "p_raw", "p_holm"])


def main() -> None:
    df = load()
    rw = expert_rewrite_means(df)

    # Canonical Aim 3 input: exactly one expert row per (page_id, model_id).
    accuracy_path = SCORES_DIR / "accuracy.csv"
    rw.to_csv(accuracy_path, index=False)

    omnibus = across_model(rw)
    out = {
        "aim3_compiled_coverage.csv": coverage(df),
        "aim3_compiled_reviewers.csv": reviewers(df),
        "aim3_compiled_pooled.csv": pooled(df),
        "aim3_compiled_by_model_primary.csv": by_model_primary(rw),
        "aim3_compiled_by_model.csv": by_model(df),
        "aim3_compiled_irr.csv": irr(df),
        "aim3_compiled_presentation_effect.csv": presentation_effect(df),
        "aim3_compiled_expert_vs_lay.csv": expert_vs_lay(df),
        "aim3_compiled_tradeoff.csv": tradeoff(rw),
        "aim3_compiled_across_model.csv": omnibus,
        "aim3_compiled_across_model_posthoc.csv": across_model_posthoc(rw, omnibus),
    }
    for name, frame in out.items():
        frame.to_csv(REPORTS_DIR / name, index=False)
        print(f"\n=== {name} ===")
        print(frame.round(4).to_string(index=False))
    print(f"\nWrote {len(out)} tables to {REPORTS_DIR}")
    print(f"Wrote canonical Aim 3 input ({len(rw)} rewrites) to {accuracy_path}")


if __name__ == "__main__":
    main()
