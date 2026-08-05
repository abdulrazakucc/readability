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
labeled ones (see CLAUDE.md: `12`'s glob would silently merge them). Re-runnable
and idempotent; reads only committed inputs. This is an INTERIM compilation
(one labeled expert for set C is still pending) and does not replace the locked
final analysis in 07_run_statistics.py.

Writes reports/aim3_compiled_*.csv.
"""

from __future__ import annotations

import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.config import REPORTS_DIR, REVIEW_DIR, SCORES_DIR  # noqa: E402

SCORES_ROOT = REVIEW_DIR / "questionnaire_scores"
AXES = ["accuracy_1_5", "completeness_1_5", "added_errors_1_5"]
MODEL_ORDER = ["claude", "openai", "gemini"]
MODEL_LABEL = {"claude": "Claude Opus 4.8", "openai": "GPT-5.5", "gemini": "Gemini 3.1 Pro"}


def load() -> pd.DataFrame:
    frames = []
    for f in sorted(SCORES_ROOT.rglob("aim3_scores_*.csv")):
        d = pd.read_csv(f)
        s = f.stem.lower()
        d["reviewer_type"] = "layperson" if ("layman" in s or "layperson" in s) else "expert"
        d["presentation"] = "neutral" if "neutral" in s else "standard"
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
        df.reviewer_type == "layperson", "layperson",
        np.where(df.presentation == "neutral", "expert_neutral", "expert_labeled"),
    )
    return df


def coverage(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in ["expert_labeled", "expert_neutral", "layperson"]:
        g = df[df.condition == c]
        rows.append({
            "condition": c,
            "reviewers": g.reviewer_name.nunique(),
            "ratings": len(g),
            "rewrites_covered": g.blind_id.nunique(),
            "sets": ", ".join(sorted(g.set_id.astype(str).unique())),
        })
    return pd.DataFrame(rows)


def by_model(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in ["expert_labeled", "expert_neutral", "layperson"]:
        for m in MODEL_ORDER:
            g = df[(df.condition == c) & (df.model_id == m)]
            r = {"condition": c, "model_id": m, "model": MODEL_LABEL[m], "n": len(g)}
            for ax in AXES:
                r[f"{ax}_mean"] = g[ax].mean()
                r[f"{ax}_sd"] = g[ax].std(ddof=1)
            r["pct_accuracy_max"] = 100 * (g.accuracy_1_5 == 5).mean()
            rows.append(r)
    return pd.DataFrame(rows)


def pooled(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in ["expert_labeled", "expert_neutral", "layperson"]:
        g = df[df.condition == c]
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
    """Pairwise agreement among labeled experts on multiply-scored rewrites."""
    lab = df[df.condition == "expert_labeled"]
    rows = []
    for ax in AXES:
        piv = lab.pivot_table(index="blind_id", columns="reviewer_name", values=ax, aggfunc="first")
        ex, w1 = [], []
        for _, r in piv.iterrows():
            vals = r.dropna().values
            for a, b in combinations(vals, 2):
                ex.append(a == b)
                w1.append(abs(a - b) <= 1)
        rows.append({"axis": ax, "rater_pairs": len(ex),
                     "pct_exact": 100 * np.mean(ex) if ex else np.nan,
                     "pct_within_1": 100 * np.mean(w1) if w1 else np.nan})
    return pd.DataFrame(rows)


def presentation_effect(df: pd.DataFrame) -> pd.DataFrame:
    """Labeled vs neutral experts (between-reviewer; confounded by rater identity)."""
    rows = []
    for _scope, m in [("overall", None)] + [("model", m) for m in MODEL_ORDER]:
        lab = df[df.condition == "expert_labeled"]
        neu = df[df.condition == "expert_neutral"]
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
    lay = df[df.condition == "layperson"]
    for ax in AXES:
        a, b = lab[ax].dropna(), lay[ax].dropna()
        rows.append({"axis": ax, "expert_mean": a.mean(), "layperson_mean": b.mean(),
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
