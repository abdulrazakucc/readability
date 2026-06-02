"""Sanity tests for the readability scorer.

If textstat changes its internal algorithm in a future release these will fail
loudly — which is intentional. Update both the textstat pin in requirements
AND the expected values here, deliberately.
"""

from __future__ import annotations

import math

import pytest

from src.readability import meets_sixth_grade, score


def test_score_on_simple_text():
    text = (
        "The cat sat on the mat. The dog ran in the yard. "
        "The sun is bright. We had fun."
    )
    s = score(text)
    assert s.word_count > 0
    assert s.sentence_count >= 4
    # Simple text should land at or below 6th-grade FKGL
    assert s.fkgl < 6.0
    assert meets_sixth_grade(s)


def test_score_on_complex_text():
    text = (
        "Transcatheter aortic valve replacement utilizes a minimally invasive "
        "endovascular approach to deploy a bioprosthetic valve within the "
        "stenotic native aortic annulus, obviating the need for cardiopulmonary "
        "bypass and sternotomy in selected high-risk surgical candidates."
    )
    s = score(text)
    # Dense medical text should clearly exceed 6th-grade
    assert s.fkgl > 6.0
    assert s.gfi > 6.0
    assert not meets_sixth_grade(s)


def test_score_on_empty_text_does_not_crash():
    s = score("")
    assert s.word_count == 0
    assert math.isnan(s.fkgl)


def test_scorer_version_is_recorded():
    s = score("Hello world. Goodbye world.")
    assert s.scorer_version.startswith("textstat-")
