"""Tests for the manuscript value extractor.

The extractor is the independent reference the whole validation harness rests on.
If it silently stops matching a sentence, checks vanish and the run still looks
green -- so the completeness assertion at the bottom matters as much as the
parsing ones.
"""

from __future__ import annotations

import pytest

from src.config import REPO_ROOT
from src.manuscript import Reported, load_reported, normalize

MANUSCRIPT = REPO_ROOT / "publication" / "Naeem_final_clean_cardiac_CT_readability.docx"
pytestmark = pytest.mark.skipif(
    not MANUSCRIPT.exists(),
    reason="manuscript lives in gitignored publication/; skip where it is absent",
)


def test_normalize_folds_word_typography():
    # U+2212 minus, en dash, non-breaking space, Greek, superscripts.
    assert normalize("−5.52") == "-5.52"
    assert normalize("4.88–6.60") == "4.88-6.60"
    assert normalize("ρ = −0.37") == "rho = -0.37"
    assert normalize("χ² = 38.0") == "chi2 = 38.0"
    assert normalize("P = .06") == "P = .06"


def test_tolerance_follows_printed_precision():
    """A value printed to 2dp is only claimed to 2dp."""
    assert Reported("k", 4.84, "4.84", 2, "T").tolerance == pytest.approx(0.005)
    assert Reported("k", 0.774, "0.774", 3, "T").tolerance == pytest.approx(0.0005)
    assert Reported("k", 155, "155", 0, "T").tolerance == pytest.approx(0.5)


def test_extracts_table_values():
    v = load_reported(MANUSCRIPT)
    assert v["t1.fkgl.mean"].value == pytest.approx(10.54)
    assert v["t1.fkgl.median"].value == pytest.approx(10.31)
    assert v["t2.fkgl.claude.delta"].value == pytest.approx(-5.52)
    assert v["t2.fkgl.claude.ci_low"].value == pytest.approx(-6.32)
    assert v["t2.fkgl.claude.ci_high"].value == pytest.approx(-4.71)
    assert v["t3.gemini.completeness.mean"].value == pytest.approx(4.64)
    assert v["t4.openai.accuracy.mean"].value == pytest.approx(5.00)


def test_extracts_prose_values_including_word_numbers():
    v = load_reported(MANUSCRIPT)
    # "Zero of 26 included pages" and "Six cardiothoracic radiologists"
    assert v["p.benchmark.meeting"].value == 0
    assert v["p.benchmark.n"].value == 26
    assert v["p.aim3.n_reviewers"].value == 6
    assert v["p.aim3.n_ratings"].value == 155
    assert v["p.lay.n_ratings"].value == 385
    assert v["p.rho.gemini"].value == pytest.approx(-0.37)
    assert v["p.ac1.accuracy"].value == pytest.approx(0.77)
    assert v["p.kappa.added_errors"].value == pytest.approx(-0.03)


def test_extraction_is_complete():
    """Guard against a silent drop in coverage.

    A pattern that stops matching removes checks without failing anything, which
    is the most dangerous way for this harness to rot. Pin the count and the
    presence of every group.
    """
    v = load_reported(MANUSCRIPT)
    assert len(v) >= 200, f"extraction shrank to {len(v)} values -- a pattern stopped matching"
    for prefix in ("t1.", "t2.", "t3.", "t4.", "p."):
        assert any(k.startswith(prefix) for k in v), f"no values extracted for {prefix}"
