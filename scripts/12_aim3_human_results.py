"""Aim 3 — compile the human-review results (interim).

Reads every returned reviewer sheet under data/review/questionnaire_scores/ and
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

SCORES_ROOT = REVIEW_DIR / "questionnaire_scores"
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

# Reviewer identity is taken from the file NAME slug, not the free-text
# `reviewer_name` field, which is inconsistent across returns (eg, "Hafsa" vs
# "Hafsa Awan", "MUHAMMAD NAEEM" vs "Muhammad Naeem"). The slug is stable, so it
# is the canonical id used for counting reviewers and pairing raters.
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
    df = df.merge(pd.read_csv(REVIEW_DIR / "blind_key.csv"), on="blind_id", how="left", validate="many_to_one")
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
    rows = []
    for c in CONDITIONS:
        g = df[df.condition == c]
        rows.append({
            "condition": c,
            "condition_label": CONDITION_LABEL[c],
            "reviewers": g.reviewer_id.nunique(),
            "ratings": len(g),
            "rewrites_covered": g.blind_id.nunique(),
            "rewrites_total": 77,
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
                         "gwet_ac1": gwet_ac1(piv) if len(piv.columns) > 1 else np.nan,
                         "gwet_ac1_fixed_scale": (
                             gwet_ac1(piv, RATING_CATEGORIES) if len(piv.columns) > 1 else np.nan
                         ),
                         "quad_weighted_kappa": (
                             mean_pairwise_weighted_kappa(piv) if len(piv.columns) > 1 else np.nan
                         )})
    return pd.DataFrame(rows)


def presentation_effect(df: pd.DataFrame) -> pd.DataFrame:
    """Labeled vs neutral presentation, WITHIN the lay cohort.

    Both presentations were scored by lay readers (2 labeled, 3 neutral), so this
    is the contrast the manuscript reports. Different people scored each
    presentation, so the effect is confounded with rater identity and is
    descriptive only -- it is not evidence of an AI-labeling effect.

    The subspecialists are not used here: only one expert (M.N.) scored the
    neutral instrument, which is too thin to support the contrast.
    """
    rows = []
    for _scope, m in [("overall", None)] + [("model", m) for m in MODEL_ORDER]:
        lab = df[df.condition == "layperson_labeled"]
        neu = df[df.condition == "layperson_neutral"]
        if m:
            lab, neu = lab[lab.model_id == m], neu[neu.model_id == m]
        for ax in AXES:
            a, b = lab[ax].dropna(), neu[ax].dropna()
            p = stats.mannwhitneyu(a, b, alternative="two-sided")[1] if len(a) and len(b) else np.nan
            rows.append({"scope": m or "overall", "axis": ax,
                         "labeled_mean": a.mean(), "labeled_n": len(a),
                         "neutral_mean": b.mean(), "neutral_n": len(b),
                         "mannwhitney_p": p})
    return pd.DataFrame(rows)


def expert_vs_lay(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    lab = df[df.condition == "expert_labeled"]
    lay = df[df.condition.isin(LAY_CONDITIONS)]  # pooled across both presentations
    for ax in AXES:
        a, b = lab[ax].dropna(), lay[ax].dropna()
        rows.append({"axis": ax, "expert_mean": a.mean(), "expert_n": len(a),
                     "layperson_mean": b.mean(), "layperson_n": len(b),
                     "mannwhitney_p": stats.mannwhitneyu(a, b, alternative="two-sided")[1]})
    return pd.DataFrame(rows)


def tradeoff(df: pd.DataFrame) -> pd.DataFrame:
    deltas = pd.read_csv(SCORES_DIR / "deltas.csv")[["page_id", "model_id", "fkgl_delta"]]
    lab = df[df.condition == "expert_labeled"]
    pm = lab.groupby(["page_id", "model_id"])[AXES].mean().reset_index().merge(deltas, on=["page_id", "model_id"])
    pm["reduction"] = -pm["fkgl_delta"]
    rows = []
    for m in MODEL_ORDER:
        s = pm[pm.model_id == m]
        rho, p = stats.spearmanr(s["reduction"], s["accuracy_1_5"])
        rows.append({"model_id": m, "model": MODEL_LABEL[m], "n_pages": len(s),
                     "spearman_rho_reduction_vs_accuracy": rho, "p_value": p})
    return pd.DataFrame(rows)


def across_model(df: pd.DataFrame) -> pd.DataFrame:
    """Friedman across the 3 models on per-page mean (labeled experts)."""
    lab = df[df.condition == "expert_labeled"]
    rows = []
    for ax in AXES:
        wide = lab.pivot_table(index="page_id", columns="model_id", values=ax, aggfunc="mean")
        wide = wide.dropna(subset=MODEL_ORDER)
        if len(wide) >= 3:
            chi2, p = stats.friedmanchisquare(*[wide[m] for m in MODEL_ORDER])
            rows.append({"axis": ax, "n_pages": len(wide),
                         "claude": wide.claude.mean(), "openai": wide.openai.mean(),
                         "gemini": wide.gemini.mean(), "friedman_chi2": chi2, "p_value": p})
    return pd.DataFrame(rows)


def main() -> None:
    df = load()
    out = {
        "aim3_compiled_coverage.csv": coverage(df),
        "aim3_compiled_reviewers.csv": reviewers(df),
        "aim3_compiled_pooled.csv": pooled(df),
        "aim3_compiled_by_model.csv": by_model(df),
        "aim3_compiled_irr.csv": irr(df),
        "aim3_compiled_presentation_effect.csv": presentation_effect(df),
        "aim3_compiled_expert_vs_lay.csv": expert_vs_lay(df),
        "aim3_compiled_tradeoff.csv": tradeoff(df),
        "aim3_compiled_across_model.csv": across_model(df),
    }
    for name, frame in out.items():
        frame.to_csv(REPORTS_DIR / name, index=False)
        print(f"\n=== {name} ===")
        print(frame.round(3).to_string(index=False))
    print(f"\nWrote {len(out)} tables to {REPORTS_DIR}")


if __name__ == "__main__":
    main()
