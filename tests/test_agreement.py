"""Tests for the inter-rater agreement coefficients.

These pin the coefficients against hand-computable cases. If a refactor changes
a number here, that is a real change in reported agreement, not a rounding
detail -- treat a failure as a finding, not a nuisance.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src.agreement import (
    RATING_CATEGORIES,
    gwet_ac1,
    mean_pairwise_weighted_kappa,
    pairwise_percent_agreement,
    quadratic_weighted_kappa,
)


def test_ac1_perfect_agreement_is_one():
    df = pd.DataFrame({"r1": [5, 4, 3, 2], "r2": [5, 4, 3, 2]})
    assert gwet_ac1(df) == pytest.approx(1.0)


def test_ac1_handles_the_ceiling_case():
    """All raters give 5 on every item.

    Under the fixed 1-5 scale this is perfect agreement (1.0) -- the behaviour
    that makes AC1 worth reporting where kappa collapses. With the category set
    derived from the data there is only one category, so chance agreement is
    undefined and the answer is NaN rather than a spurious 1.0.
    """
    df = pd.DataFrame({"r1": [5] * 10, "r2": [5] * 10})
    assert gwet_ac1(df) == pytest.approx(1.0)
    # Cohen's kappa is undefined here (both raters use one category).
    assert np.isnan(quadratic_weighted_kappa(df.r1.to_numpy(), df.r2.to_numpy()))


def test_ac1_uses_the_protocol_scale_not_the_observed_categories():
    """q is a design fact, so categories nobody used still count.

    Pinning this stops the default drifting to a data-derived q, which would
    change every published agreement figure.
    """
    df = pd.DataFrame({"r1": [5, 5, 5, 4, 5, 4], "r2": [5, 5, 4, 4, 5, 5]})
    protocol = gwet_ac1(df)           # default: q = 5
    observed = gwet_ac1(df, (4, 5))   # what a data-derived q would give
    assert protocol > observed
    assert protocol - observed > 0.1


def test_ac1_matches_hand_computation():
    """Two raters, 4 items, 3 agreements and 1 disagreement, 5 categories.

    p_a = 3/4 = 0.75.
    Prevalences over 8 ratings: 5 -> 5/8 counted per item as means.
      item means: (5,5)->pi5 1.0 ; (5,5)->1.0 ; (4,4)-> pi4 1.0 ; (5,4)-> .5/.5
      pi_5 = (1 + 1 + 0 + .5)/4 = 0.625 ; pi_4 = (0 + 0 + 1 + .5)/4 = 0.375
    p_e = [pi5(1-pi5) + pi4(1-pi4)] / (5-1)
        = [0.625*0.375 + 0.375*0.625] / 4 = 0.46875/4 = 0.1171875
    AC1 = (0.75 - 0.1171875)/(1 - 0.1171875) = 0.716814...
    """
    df = pd.DataFrame({"r1": [5, 5, 4, 5], "r2": [5, 5, 4, 4]})
    assert gwet_ac1(df, RATING_CATEGORIES) == pytest.approx(0.7168141592920354, rel=1e-9)


def test_ac1_ignores_items_rated_once():
    """An item with a single rater carries no agreement information."""
    paired = pd.DataFrame({"r1": [5, 4], "r2": [5, 4]})
    with_singleton = pd.DataFrame({"r1": [5, 4, 3], "r2": [5, 4, np.nan]})
    assert gwet_ac1(with_singleton, RATING_CATEGORIES) == pytest.approx(
        gwet_ac1(paired, RATING_CATEGORIES))


def test_ac1_returns_nan_without_any_paired_item():
    df = pd.DataFrame({"r1": [5, 4], "r2": [np.nan, np.nan]})
    assert np.isnan(gwet_ac1(df))


def test_weighted_kappa_perfect_and_ordering():
    """Quadratic weights make a near-miss count more than a far miss."""
    a = np.array([1, 2, 3, 4, 5])
    assert quadratic_weighted_kappa(a, a) == pytest.approx(1.0)

    near = quadratic_weighted_kappa(np.array([5, 4, 3, 2, 1]), np.array([5, 4, 3, 2, 2]))
    far = quadratic_weighted_kappa(np.array([5, 4, 3, 2, 1]), np.array([5, 4, 3, 2, 5]))
    assert near > far


def test_weighted_kappa_symmetric():
    a = np.array([5, 4, 5, 3, 4])
    b = np.array([4, 4, 5, 2, 5])
    assert quadratic_weighted_kappa(a, b) == pytest.approx(quadratic_weighted_kappa(b, a))


def test_kappa_is_zero_when_one_rater_is_constant():
    """A rater with no variance is uninformative: chance-corrected agreement is 0.

    This is not a defect -- it is the mechanism behind the ceiling paradox. When
    most raters sit on 5, many pairs contribute exactly 0 and the mean kappa is
    dragged toward zero even though raw agreement is excellent.
    """
    varying = np.array([5, 4, 3, 5])
    constant = np.array([5, 5, 5, 5])
    assert quadratic_weighted_kappa(varying, constant) == pytest.approx(0.0)


def test_kappa_is_undefined_only_when_both_raters_are_constant():
    """Both raters pinned to one category leaves expected agreement at 1: undefined."""
    both_constant = np.array([5, 5, 5, 5])
    assert np.isnan(quadratic_weighted_kappa(both_constant, both_constant))


def test_mean_pairwise_kappa_skips_only_undefined_pairs():
    """Undefined pairs are dropped; informative-but-zero pairs are kept.

    r1/r2 vary; r3 is constant, so r1-r3 and r2-r3 are defined and equal 0.
    The mean is therefore (k12 + 0 + 0)/3, not k12 alone.
    """
    df = pd.DataFrame({"r1": [5, 4, 3, 5], "r2": [5, 4, 3, 4], "r3": [5, 5, 5, 5]})
    k12 = quadratic_weighted_kappa(df.r1.to_numpy(), df.r2.to_numpy())
    assert mean_pairwise_weighted_kappa(df) == pytest.approx((k12 + 0.0 + 0.0) / 3)

    # A pair that is genuinely undefined must not be counted at all.
    df2 = pd.DataFrame({"r1": [5, 4, 3, 5], "r2": [5, 4, 3, 4], "r3": [5, 5, 5, 5],
                        "r4": [5, 5, 5, 5]})
    # r3-r4 is undefined (both constant); the other five pairs are defined.
    assert not np.isnan(mean_pairwise_weighted_kappa(df2))


def test_percent_agreement_counts_every_pair():
    """3 raters on 1 item -> 3 pairs, not 1."""
    df = pd.DataFrame({"r1": [5], "r2": [5], "r3": [4]})
    out = pairwise_percent_agreement(df)
    assert out["rater_pairs"] == 3
    assert out["pct_exact"] == pytest.approx(100 * 1 / 3)
    assert out["pct_within_1"] == pytest.approx(100.0)


# --- Cross-check against Gwet's reference implementation -------------------
# Installing `irrCAC` is optional; where it is present these tests pin how our
# implementation relates to it, including where the two legitimately disagree.

irrCAC_raw = pytest.importorskip("irrCAC.raw", reason="irrCAC not installed")


def _matrix():
    """Ratings that only ever use the top two categories -- the ceiling shape."""
    return pd.DataFrame({
        "r1": [5, 5, 4, 5, 5, 4, 5, 5],
        "r2": [5, 4, 4, 5, 5, 5, 5, 4],
        "r3": [5, 5, 4, 4, 5, 5, 5, 5],
    })


def test_protocol_scale_ac1_exceeds_the_reference_package_under_a_ceiling():
    """Documents a real, expected divergence from the irrCAC package.

    irrCAC builds its agreement matrix from the categories present in the data, so
    under a ceiling it uses a smaller q and returns a lower coefficient than the
    protocol-scale definition. Neither is a bug -- they answer different questions.
    This test exists so the gap stays visible and nobody later "fixes" our value to
    match the package.
    """
    m = _matrix()
    ours = gwet_ac1(m)
    ref = irrCAC_raw.CAC(m.copy()).gwet()["est"]["coefficient_value"]
    assert ours > ref
