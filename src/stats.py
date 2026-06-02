"""Statistical analysis implementations per `docs/statistical_analysis_plan.md`.

This file is intended to be LOCKED at Phase-5 start (no edits to test logic
afterward). If the data forces a deviation, log it in `docs/stats_deviations.md`
and document the rationale in code with a dated comment.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

SCORE_COLS = ["fkre", "fkgl", "gfi", "smog", "cli", "ari"]


# --- Aim 1 -------------------------------------------------------------------

def describe_by(df: pd.DataFrame, group_col: str, score_cols: Iterable[str] = SCORE_COLS) -> pd.DataFrame:
    rows = []
    for group, sub in df.groupby(group_col):
        for col in score_cols:
            vals = sub[col].dropna()
            rows.append(
                {
                    "group": group,
                    "score": col,
                    "n": len(vals),
                    "mean": vals.mean(),
                    "sd": vals.std(ddof=1) if len(vals) > 1 else np.nan,
                    "median": vals.median(),
                    "iqr_low": vals.quantile(0.25),
                    "iqr_high": vals.quantile(0.75),
                }
            )
    return pd.DataFrame(rows)


def _is_approx_normal(values: np.ndarray, alpha: float = 0.05) -> bool:
    if len(values) < 3:
        return False
    try:
        _, p = stats.shapiro(values)
    except ValueError:
        return False
    return p > alpha


def aim1_across_groups(
    df: pd.DataFrame,
    group_col: str,
    score_cols: Iterable[str] = SCORE_COLS,
) -> pd.DataFrame:
    """One-way comparison across levels of `group_col` (e.g., site, procedure).

    Decision rule: ANOVA if normal-ish AND homoscedastic, else Kruskal-Wallis.
    """
    rows = []
    for col in score_cols:
        groups = [g[col].dropna().values for _, g in df.groupby(group_col)]
        groups = [g for g in groups if len(g) >= 2]
        if len(groups) < 2:
            rows.append({"score": col, "test": "skipped", "statistic": np.nan, "p": np.nan, "n_groups": len(groups)})
            continue

        all_normal = all(_is_approx_normal(g) for g in groups)
        try:
            _, levene_p = stats.levene(*groups, center="median")
        except ValueError:
            levene_p = 0.0
        homosced = levene_p > 0.05

        if all_normal and homosced:
            stat, p = stats.f_oneway(*groups)
            test = "anova"
        else:
            stat, p = stats.kruskal(*groups)
            test = "kruskal"

        rows.append(
            {
                "score": col,
                "test": test,
                "statistic": float(stat),
                "p": float(p),
                "n_groups": len(groups),
                "levene_p": float(levene_p),
            }
        )
    return pd.DataFrame(rows)


def fraction_meeting_benchmark(df: pd.DataFrame, fkgl_threshold: float = 6.0) -> dict:
    n = len(df)
    if n == 0:
        return {"n": 0, "meeting": 0, "fraction": float("nan")}
    meeting = (df["fkgl"] <= fkgl_threshold).sum()
    return {"n": int(n), "meeting": int(meeting), "fraction": float(meeting) / n}


# --- Aim 2 -------------------------------------------------------------------

@dataclass
class PairedResult:
    score: str
    model_id: str
    n: int
    mean_delta: float
    ci_low: float
    ci_high: float
    test: str
    statistic: float
    p_raw: float
    effect_size: float


def _paired_ci(deltas: np.ndarray, conf: float = 0.95) -> tuple[float, float]:
    n = len(deltas)
    if n < 2:
        return (np.nan, np.nan)
    mean = deltas.mean()
    se = deltas.std(ddof=1) / np.sqrt(n)
    t_crit = stats.t.ppf(0.5 + conf / 2, df=n - 1)
    return (mean - t_crit * se, mean + t_crit * se)


def aim2_paired_per_model(
    originals: pd.DataFrame,
    rewrites: pd.DataFrame,
    score_cols: Iterable[str] = SCORE_COLS,
) -> pd.DataFrame:
    """Paired tests of original vs each model's rewrite, per score.

    `originals` keyed by page_id. `rewrites` keyed by (page_id, model_id).
    Both have the SCORE_COLS columns. Applies Holm-Bonferroni across the full
    family of paired tests.
    """
    results: list[PairedResult] = []
    for model_id, sub in rewrites.groupby("model_id"):
        merged = sub.merge(
            originals[["page_id", *score_cols]],
            on="page_id",
            suffixes=("_rewrite", "_orig"),
        )
        for col in score_cols:
            deltas = (merged[f"{col}_rewrite"] - merged[f"{col}_orig"]).dropna().values
            n = len(deltas)
            if n < 2:
                continue
            mean_delta = float(deltas.mean())
            ci_low, ci_high = _paired_ci(deltas)

            if _is_approx_normal(deltas):
                stat, p = stats.ttest_rel(merged[f"{col}_rewrite"], merged[f"{col}_orig"])
                test = "paired_t"
                effect = mean_delta / deltas.std(ddof=1) if deltas.std(ddof=1) > 0 else 0.0
            else:
                stat, p = stats.wilcoxon(merged[f"{col}_rewrite"], merged[f"{col}_orig"])
                test = "wilcoxon"
                # rank-biserial via Wilcoxon W
                effect = float(stat) / (n * (n + 1) / 2) if n > 0 else 0.0

            results.append(
                PairedResult(
                    score=col,
                    model_id=model_id,
                    n=n,
                    mean_delta=mean_delta,
                    ci_low=ci_low,
                    ci_high=ci_high,
                    test=test,
                    statistic=float(stat),
                    p_raw=float(p),
                    effect_size=float(effect),
                )
            )

    df = pd.DataFrame([r.__dict__ for r in results])
    if len(df) > 0:
        _, p_adj, _, _ = multipletests(df["p_raw"], method="holm")
        df["p_holm"] = p_adj
    return df


def aim2_across_models(
    rewrites: pd.DataFrame,
    score_cols: Iterable[str] = SCORE_COLS,
) -> pd.DataFrame:
    """Per score, test whether the three models differ in post-rewrite values.

    Uses Friedman test (paired across pages by model). Repeated-measures ANOVA
    parametric path is left as an optional future addition since Friedman is
    robust and non-parametric.
    """
    rows = []
    for col in score_cols:
        pivot = rewrites.pivot_table(index="page_id", columns="model_id", values=col, aggfunc="first")
        pivot = pivot.dropna()
        if pivot.shape[1] < 3 or len(pivot) < 3:
            rows.append({"score": col, "test": "skipped", "statistic": np.nan, "p": np.nan, "n_pages": len(pivot)})
            continue
        stat, p = stats.friedmanchisquare(*[pivot[m].values for m in pivot.columns])
        rows.append(
            {
                "score": col,
                "test": "friedman",
                "statistic": float(stat),
                "p": float(p),
                "n_pages": len(pivot),
                "models": list(pivot.columns),
            }
        )
    return pd.DataFrame(rows)


# --- Aim 3 -------------------------------------------------------------------

def aim3_tradeoff_correlations(
    deltas: pd.DataFrame,
    accuracy: pd.DataFrame,
    primary_score: str = "fkgl",
) -> pd.DataFrame:
    """Per model, Spearman correlation between reading-level drop and accuracy/completeness.

    `deltas` has columns: page_id, model_id, <score>_delta (post - pre).
    `accuracy` has: page_id, model_id, accuracy_1_5, completeness_1_5, added_errors_1_5.
    """
    delta_col = f"{primary_score}_delta"
    merged = deltas.merge(accuracy, on=["page_id", "model_id"], how="inner")
    rows = []
    for model_id, sub in merged.groupby("model_id"):
        for axis in ("accuracy_1_5", "completeness_1_5", "added_errors_1_5"):
            sub2 = sub[[delta_col, axis]].dropna()
            if len(sub2) < 4:
                rows.append({"model_id": model_id, "axis": axis, "n": len(sub2), "rho": np.nan, "p": np.nan})
                continue
            rho, p = stats.spearmanr(sub2[delta_col], sub2[axis])
            rows.append(
                {
                    "model_id": model_id,
                    "axis": axis,
                    "n": int(len(sub2)),
                    "rho": float(rho),
                    "p": float(p),
                }
            )
    return pd.DataFrame(rows)


def aim3_clinical_model_comparison(accuracy: pd.DataFrame) -> pd.DataFrame:
    """Friedman test across models on each clinical dimension."""
    rows = []
    for axis in ("accuracy_1_5", "completeness_1_5", "added_errors_1_5"):
        pivot = accuracy.pivot_table(index="page_id", columns="model_id", values=axis, aggfunc="first").dropna()
        if pivot.shape[1] < 3 or len(pivot) < 3:
            rows.append({"axis": axis, "test": "skipped", "statistic": np.nan, "p": np.nan, "n_pages": len(pivot)})
            continue
        stat, p = stats.friedmanchisquare(*[pivot[m].values for m in pivot.columns])
        rows.append(
            {
                "axis": axis,
                "test": "friedman",
                "statistic": float(stat),
                "p": float(p),
                "n_pages": int(len(pivot)),
            }
        )
    return pd.DataFrame(rows)
