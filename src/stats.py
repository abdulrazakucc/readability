"""Statistical analysis implementations per `docs/statistical_analysis_plan.md`.

This file is intended to be LOCKED at Phase-5 start (no edits to test logic
afterward). If the data forces a deviation, log it in `docs/stats_deviations.md`
and document the rationale in code with a dated comment.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import combinations

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

def rank_biserial_from_differences(diff: np.ndarray) -> float:
    """Signed matched-pairs rank-biserial correlation for a Wilcoxon signed-rank test.

    r = (W+ - W-) / (W+ + W-), computed on the ranks of |difference| after dropping
    zero differences, matching scipy's default zero handling.

    The previous implementation used W / [n(n+1)/2], which is unsigned and does not
    reach +/-1 when every difference points the same way: Gemini's GFI, SMOG and ARI
    all had W = 0 with every difference negative, yet reported an effect size of 0.0
    instead of -1.0. Sign convention here follows rewrite - original, so a uniform
    reduction in grade level gives -1.0.
    """
    diff = np.asarray(diff, dtype=float)
    diff = diff[np.isfinite(diff) & (diff != 0)]
    if diff.size == 0:
        return 0.0
    ranks = stats.rankdata(np.abs(diff), method="average")
    w_pos = float(ranks[diff > 0].sum())
    w_neg = float(ranks[diff < 0].sum())
    total = w_pos + w_neg
    return (w_pos - w_neg) / total if total > 0 else 0.0


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
                effect = rank_biserial_from_differences(deltas)

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
    # Correlate POSITIVE reduction (original - rewrite), so a larger x means more
    # grade levels removed. The stored delta is rewrite - original, i.e. negative for
    # a simplification; correlating it directly inverted the sign relative to the
    # figures, which already plot -delta.
    delta_col = f"{primary_score}_reduction"
    merged = deltas.merge(accuracy, on=["page_id", "model_id"], how="inner")
    merged[delta_col] = -merged[f"{primary_score}_delta"]
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


# --- Post-protocol additions (see docs/stats_deviations.md, 2026-08-10) --------

PROJECT_SEED = 42


def pairwise_posthoc_models(
    wide: pd.DataFrame,
    models: Iterable[str],
    label: str = "",
) -> pd.DataFrame:
    """Paired Wilcoxon post-hoc across every model pair, Holm-adjusted within `label`.

    `wide` is one row per unit (page) with one column per model, already restricted
    to units complete across all models. The SAP requires pairwise follow-up after a
    significant omnibus test; only the omnibus was implemented, so this closes that
    gap.
    """
    models = list(models)
    rows = []
    for a, b in combinations(models, 2):
        pair = wide[[a, b]].dropna()
        if len(pair) < 2:
            continue
        stat, p = stats.wilcoxon(pair[a], pair[b])
        rows.append({
            "label": label, "model_a": a, "model_b": b, "n_pairs": int(len(pair)),
            "mean_a": float(pair[a].mean()), "mean_b": float(pair[b].mean()),
            "median_diff": float((pair[a] - pair[b]).median()),
            "wilcoxon_stat": float(stat), "p_raw": float(p),
            "effect_size_rank_biserial": rank_biserial_from_differences(
                (pair[a] - pair[b]).to_numpy()),
        })
    out = pd.DataFrame(rows)
    if len(out):
        _, p_adj, _, _ = multipletests(out["p_raw"], method="holm")
        out["p_holm"] = p_adj
    return out


def spearman_bootstrap_ci(
    x: np.ndarray,
    y: np.ndarray,
    n_boot: int = 5000,
    seed: int = PROJECT_SEED,
) -> dict:
    """Spearman rho with a percentile bootstrap CI over resampled units.

    Units are resampled with replacement; degenerate resamples (no variance in
    either vector) are skipped rather than counted as rho = 0, which would pull the
    interval toward the middle. The seed is fixed so the interval is reproducible.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = len(x)
    if n < 4:
        return {"n": n, "rho": np.nan, "ci_low": np.nan, "ci_high": np.nan,
                "p_value": np.nan, "n_boot_valid": 0}
    rho, p = stats.spearmanr(x, y)
    rng = np.random.default_rng(seed)
    boots = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, n)
        xb, yb = x[idx], y[idx]
        if np.ptp(xb) == 0 or np.ptp(yb) == 0:
            continue
        r = stats.spearmanr(xb, yb).statistic
        if np.isfinite(r):
            boots.append(r)
    if boots:
        lo, hi = np.percentile(boots, [2.5, 97.5])
    else:
        lo = hi = np.nan
    return {"n": int(n), "rho": float(rho), "ci_low": float(lo), "ci_high": float(hi),
            "p_value": float(p), "n_boot_valid": len(boots)}


def dunn_posthoc(groups: dict[str, np.ndarray], method: str = "holm") -> pd.DataFrame:
    """Dunn's test for every group pair after a significant Kruskal-Wallis.

    Uses the pooled mid-rank standard error with a tie correction, then adjusts the
    pairwise family. Implemented here because the SAP requires post-hoc follow-up
    and only the omnibus existed.
    """
    names = [k for k, v in groups.items() if len(v) > 0]
    all_vals = np.concatenate([np.asarray(groups[k], dtype=float) for k in names])
    all_ranks = stats.rankdata(all_vals)
    N = len(all_vals)
    sizes, mean_ranks, pos = {}, {}, 0
    for k in names:
        m = len(groups[k])
        sizes[k] = m
        mean_ranks[k] = all_ranks[pos:pos + m].mean()
        pos += m
    _, counts = np.unique(all_vals, return_counts=True)
    ties = float((counts ** 3 - counts).sum())
    sigma2 = (N * (N + 1) / 12.0) - ties / (12.0 * (N - 1)) if N > 1 else np.nan

    rows = []
    for a, b in combinations(names, 2):
        se = np.sqrt(sigma2 * (1.0 / sizes[a] + 1.0 / sizes[b]))
        z = (mean_ranks[a] - mean_ranks[b]) / se if se > 0 else np.nan
        p = 2 * (1 - stats.norm.cdf(abs(z))) if np.isfinite(z) else np.nan
        rows.append({"group_a": a, "group_b": b, "n_a": sizes[a], "n_b": sizes[b],
                     "mean_rank_a": mean_ranks[a], "mean_rank_b": mean_ranks[b],
                     "z": z, "p_raw": p})
    out = pd.DataFrame(rows)
    if len(out) and out["p_raw"].notna().any():
        _, p_adj, _, _ = multipletests(out["p_raw"].fillna(1.0), method=method)
        out["p_adj"] = p_adj
    return out


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact binomial CI; the beta quantile is degenerate at k = 0 and k = n."""
    lo = 0.0 if k == 0 else float(stats.beta.ppf(alpha / 2, k, n - k + 1))
    hi = 1.0 if k == n else float(stats.beta.ppf(1 - alpha / 2, k + 1, n - k))
    return lo, hi
