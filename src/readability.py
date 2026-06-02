"""Readability scoring — the six formulas the field uses.

All scores come from `textstat`. We pin and record `textstat.__version__` so a
re-run on a newer textstat is clearly distinguishable.

A sanity test in `tests/test_readability.py` validates these against fixed values
for a fixed input string. If textstat changes its algorithm in a future release,
the test will catch it.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

import textstat

_v = textstat.__version__
SCORER_VERSION = f"textstat-{'.'.join(map(str, _v)) if isinstance(_v, tuple) else _v}"


@dataclass
class ReadabilityScores:
    fkre: float  # Flesch-Kincaid Reading Ease (higher = easier)
    fkgl: float  # Flesch-Kincaid Grade Level
    gfi: float   # Gunning-Fog Index
    smog: float  # SMOG index
    cli: float   # Coleman-Liau Index
    ari: float   # Automated Readability Index
    word_count: int
    sentence_count: int
    avg_words_per_sentence: float
    avg_syllables_per_word: float
    scorer_version: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _safe_round(value: float, ndigits: int = 2) -> float:
    try:
        return round(float(value), ndigits)
    except (TypeError, ValueError):
        return float("nan")


def score(text: str) -> ReadabilityScores:
    """Score a single cleaned text. Returns a `ReadabilityScores` dataclass.

    Behavior on empty or trivially short text: returns NaN-filled scores rather
    than raising — the caller decides whether to filter.
    """
    if not text or not text.strip():
        return ReadabilityScores(
            fkre=float("nan"),
            fkgl=float("nan"),
            gfi=float("nan"),
            smog=float("nan"),
            cli=float("nan"),
            ari=float("nan"),
            word_count=0,
            sentence_count=0,
            avg_words_per_sentence=float("nan"),
            avg_syllables_per_word=float("nan"),
            scorer_version=SCORER_VERSION,
        )

    word_count = textstat.lexicon_count(text, removepunct=True)
    sentence_count = max(1, textstat.sentence_count(text))
    syllable_count = textstat.syllable_count(text)

    return ReadabilityScores(
        fkre=_safe_round(textstat.flesch_reading_ease(text)),
        fkgl=_safe_round(textstat.flesch_kincaid_grade(text)),
        gfi=_safe_round(textstat.gunning_fog(text)),
        smog=_safe_round(textstat.smog_index(text)),
        cli=_safe_round(textstat.coleman_liau_index(text)),
        ari=_safe_round(textstat.automated_readability_index(text)),
        word_count=word_count,
        sentence_count=sentence_count,
        avg_words_per_sentence=_safe_round(word_count / sentence_count, 2),
        avg_syllables_per_word=_safe_round(syllable_count / max(1, word_count), 3),
        scorer_version=SCORER_VERSION,
    )


def meets_sixth_grade(scores: ReadabilityScores) -> bool:
    """The NIH/AMA recommendation is roughly 6th-grade. Use FKGL <= 6 as the test."""
    return scores.fkgl <= 6.0
