"""Tests for the post-review corrections to the locked statistics implementation.

Each test here pins a defect the implementation review identified, so a regression
shows up as a failure rather than as a quietly wrong number in a table.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.stats import (
    clopper_pearson,
    pairwise_posthoc_models,
    rank_biserial_from_differences,
    spearman_bootstrap_ci,
)


def test_rank_biserial_is_signed_and_reaches_the_bounds():
    """The old W/[n(n+1)/2] form could not do this.

    Gemini's GFI, SMOG and ARI each had every difference negative yet reported an
    effect size of 0.0. A uniform direction must give exactly -1 or +1.
    """
    assert rank_biserial_from_differences(np.array([-1.0, -2.0, -3.0])) == pytest.approx(-1.0)
    assert rank_biserial_from_differences(np.array([1.0, 2.0, 3.0])) == pytest.approx(1.0)


def test_rank_biserial_is_near_zero_when_signs_balance():
    assert rank_biserial_from_differences(np.array([-1.0, 1.0, -2.0, 2.0])) == pytest.approx(0.0)


def test_rank_biserial_drops_zero_differences():
    """Zero differences are excluded, matching scipy's default wilcoxon handling."""
    with_zeros = rank_biserial_from_differences(np.array([-1.0, -2.0, 0.0, 0.0]))
    without = rank_biserial_from_differences(np.array([-1.0, -2.0]))
    assert with_zeros == pytest.approx(without)


def test_rank_biserial_handles_all_zero_input():
    assert rank_biserial_from_differences(np.array([0.0, 0.0])) == 0.0


def test_bootstrap_ci_is_deterministic():
    """A fixed seed must give a reproducible interval, or reported CIs drift."""
    rng = np.random.default_rng(7)
    x = rng.normal(size=40)
    y = 0.5 * x + rng.normal(size=40)
    assert spearman_bootstrap_ci(x, y) == spearman_bootstrap_ci(x, y)


def test_bootstrap_ci_brackets_the_point_estimate():
    rng = np.random.default_rng(11)
    x = rng.normal(size=60)
    y = 0.8 * x + rng.normal(size=60) * 0.3
    out = spearman_bootstrap_ci(x, y)
    assert out["ci_low"] < out["rho"] < out["ci_high"]
    assert out["n_boot_valid"] > 4000


def test_bootstrap_ci_returns_nan_when_too_few_points():
    out = spearman_bootstrap_ci(np.array([1.0, 2.0]), np.array([1.0, 2.0]))
    assert np.isnan(out["rho"])


def test_clopper_pearson_zero_successes():
    """0 of 26 must give a lower bound of exactly 0 and the exact upper bound."""
    lo, hi = clopper_pearson(0, 26)
    assert lo == 0.0
    assert hi == pytest.approx(0.1322746, abs=1e-6)


def test_clopper_pearson_all_successes():
    lo, hi = clopper_pearson(26, 26)
    assert hi == 1.0
    assert lo > 0.8


def test_pairwise_posthoc_holm_adjusts_within_family():
    """Three model pairs, Holm-adjusted; adjusted P must be >= raw P."""
    rng = np.random.default_rng(3)
    n = 25
    wide = pd.DataFrame({
        "claude": rng.normal(5, 1, n),
        "openai": rng.normal(7, 1, n),
        "gemini": rng.normal(5, 1, n),
    })
    out = pairwise_posthoc_models(wide, ["claude", "openai", "gemini"], label="fkgl")
    assert len(out) == 3
    assert (out["p_holm"] >= out["p_raw"] - 1e-12).all()
    assert set(out["label"]) == {"fkgl"}
