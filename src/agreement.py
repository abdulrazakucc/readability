"""Inter-rater agreement coefficients for the Aim 3 blinded review.

Why this module exists
----------------------
The Aim 3 ratings sit against a hard ceiling: ~86% of expert accuracy ratings are
the maximum value of 5. Under that condition Cohen's kappa collapses toward zero
even when raters agree on almost every item -- the well-known "high agreement,
low kappa" paradox (Feinstein & Cicchetti 1990). Reporting kappa alone would
misrepresent agreement as poor when it is in fact excellent.

We therefore report three complementary quantities, exactly as the manuscript does:

1. Percent agreement (exact and within-1), which is transparent but not
   chance-corrected.
2. Gwet's AC1, a chance-corrected coefficient whose expected-agreement term is
   designed to be stable under skewed marginals -- the paradox-resistant measure.
3. Quadratic-weighted Cohen's kappa, reported for completeness and expected to be
   near zero here; its collapse is the diagnostic, not a defect.

`src/stats.py` is a LOCKED artifact, so these live in their own module rather
than being added to it.

References
----------
Gwet KL. Computing inter-rater reliability and its variance in the presence of
high agreement. Br J Math Stat Psychol. 2008;61(1):29-48.
Cohen J. Weighted kappa. Psychol Bull. 1968;70(4):213-220.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np
import pandas as pd

# The three Aim 3 rubric scales are ordinal 1-5. Fixing the category set (rather
# than inferring it from observed data) keeps the chance-agreement term
# comparable across conditions, some of which never use the low categories.
RATING_CATEGORIES: tuple[int, ...] = (1, 2, 3, 4, 5)


def gwet_ac1(
    ratings: pd.DataFrame,
    categories: tuple[int, ...] | None = None,
) -> float:
    """Gwet's AC1 for an items x raters matrix, allowing missing cells.

    `ratings` is indexed by item with one column per rater; NaN means that rater
    did not score that item. Items rated by fewer than 2 raters carry no
    agreement information and are dropped.

    Uses the multiple-rater generalisation from Gwet (2008): agreement is the
    mean over items of the proportion of concordant rater pairs, and chance
    agreement is built from the mean category prevalences.

    The category set drives chance agreement, so it changes the answer materially
    -- this is not a detail:

    * `categories=None` (default) derives the categories from the data actually
      observed. This is the ONLY variant that reproduces all three published AC1
      values, and it is why it is the default.

      Be clear about the status of that choice: it was selected because it
      matches the manuscript, not because an external reference validates it.
      The `irrCAC` package -- Gwet's own reference implementation -- gives 0.782
      for subspecialist accuracy where this gives 0.771 and the manuscript prints
      0.77, so irrCAC does NOT reproduce the published value. Whether the
      published numbers came from a third implementation is unresolved and only
      the manuscript's author can settle it. `tests/test_agreement.py` pins the
      divergence so it cannot quietly drift.
    * Passing an explicit set (eg `RATING_CATEGORIES`) fixes q across cohorts,
      which makes coefficients comparable between groups that happen to use
      different parts of the scale.

    The two differ sharply under a ceiling. On this study's expert accuracy
    ratings only categories 4 and 5 ever occur, so the data-derived q is 2 and
    AC1 is 0.771, whereas fixing q=5 gives 0.805. Deriving q is the load-bearing
    choice; how prevalence is weighted (per item vs per rating) shifts the answer
    by under 0.001 and does not matter. Both q modes are correct answers to
    different questions, so `scripts/12` reports them side by side.

    Returns NaN when no item has 2 or more raters.
    """
    counts_rows = []
    for _, row in ratings.iterrows():
        vals = row.dropna().to_numpy()
        if len(vals) < 2:
            continue
        counts_rows.append(vals)
    if not counts_rows:
        return float("nan")

    if categories is None:
        categories = tuple(sorted({int(v) for vals in counts_rows for v in vals}))
    q = len(categories)
    if q < 2:
        # Every rater used a single category: agreement is perfect by
        # construction and chance agreement is undefined.
        return float("nan")

    counts, weights = [], []
    for vals in counts_rows:
        counts.append([int((vals == k).sum()) for k in categories])
        weights.append(len(vals))

    n_ik = np.asarray(counts, dtype=float)
    r = np.asarray(weights, dtype=float)

    # Observed agreement: concordant pairs / total pairs, averaged over items.
    p_a = float(np.mean((n_ik * (n_ik - 1)).sum(axis=1) / (r * (r - 1))))

    # Chance agreement from mean prevalence of each category.
    pi_k = (n_ik / r[:, None]).mean(axis=0)
    p_e = float((pi_k * (1.0 - pi_k)).sum() / (q - 1))

    if np.isclose(p_e, 1.0):
        return float("nan")
    return (p_a - p_e) / (1.0 - p_e)


def quadratic_weighted_kappa(
    a: np.ndarray,
    b: np.ndarray,
    categories: tuple[int, ...] = RATING_CATEGORIES,
) -> float:
    """Quadratic-weighted Cohen's kappa between two raters' aligned scores.

    Weights are w_ij = 1 - ((i-j)/(q-1))**2, so near-misses count as partial
    agreement. Returns NaN if fewer than 2 paired observations, or if expected
    agreement is degenerate (which happens when both raters use a single
    category -- exactly the ceiling case this module warns about).
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    mask = ~(np.isnan(a) | np.isnan(b))
    a, b = a[mask], b[mask]
    if len(a) < 2:
        return float("nan")

    q = len(categories)
    idx = {c: i for i, c in enumerate(categories)}
    i_idx = np.array([idx[int(v)] for v in a])
    j_idx = np.array([idx[int(v)] for v in b])

    obs = np.zeros((q, q), dtype=float)
    np.add.at(obs, (i_idx, j_idx), 1.0)
    obs /= obs.sum()

    row = obs.sum(axis=1)
    col = obs.sum(axis=0)
    exp = np.outer(row, col)

    ii, jj = np.meshgrid(np.arange(q), np.arange(q), indexing="ij")
    w = 1.0 - ((ii - jj) / (q - 1)) ** 2

    p_o = float((w * obs).sum())
    p_e = float((w * exp).sum())
    if np.isclose(p_e, 1.0):
        return float("nan")
    return (p_o - p_e) / (1.0 - p_e)


def mean_pairwise_weighted_kappa(
    ratings: pd.DataFrame,
    categories: tuple[int, ...] = RATING_CATEGORIES,
    min_overlap: int = 2,
) -> float:
    """Mean quadratic-weighted kappa across all rater pairs sharing >= min_overlap items.

    Cohen's kappa is defined for exactly two raters, so with a panel we average
    over pairs. Pairs whose kappa is undefined (degenerate marginals) are skipped
    rather than treated as zero, which would bias the mean downward.
    """
    ks = []
    for r1, r2 in combinations(ratings.columns, 2):
        both = ratings[[r1, r2]].dropna()
        if len(both) < min_overlap:
            continue
        k = quadratic_weighted_kappa(both[r1].to_numpy(), both[r2].to_numpy(), categories)
        if not np.isnan(k):
            ks.append(k)
    return float(np.mean(ks)) if ks else float("nan")


def pairwise_percent_agreement(ratings: pd.DataFrame) -> dict[str, float]:
    """Exact and within-1 percent agreement over all co-rated pairs.

    Counts every (rater, rater) pair on every commonly-rated item, matching how
    the manuscript reports "rater-pairs".
    """
    exact, within1 = [], []
    for _, row in ratings.iterrows():
        vals = row.dropna().to_numpy()
        for x, y in combinations(vals, 2):
            exact.append(x == y)
            within1.append(abs(x - y) <= 1)
    if not exact:
        return {"rater_pairs": 0, "pct_exact": float("nan"), "pct_within_1": float("nan")}
    return {
        "rater_pairs": len(exact),
        "pct_exact": 100.0 * float(np.mean(exact)),
        "pct_within_1": 100.0 * float(np.mean(within1)),
    }
