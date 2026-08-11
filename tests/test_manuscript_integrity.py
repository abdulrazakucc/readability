"""Structural integrity checks on the manuscript.

`test_manuscript.py` checks that values can be *extracted*; this file checks that the
document is internally coherent — the class of defect that survives a numerical audit
and is then caught by a copyeditor, or worse, a reader.

Each test encodes a defect that was actually found and fixed in this project:

  - front matter claiming a display count the document does not contain
  - a display defined but never called out in the text (a main figure, at one point)
  - an in-text reference pointing at a display that does not exist
  - a P value printed as ".00", which asserts an impossible certainty
  - display labels that skip a number or repeat one
  - the display manifest and the manuscript disagreeing after a renumbering

They read the document with tracked changes accepted, since that is the state a
reviewer will see once the revisions are applied.
"""

from __future__ import annotations

import importlib.util
import re

import pytest

from src.config import CONFIG_DIR, REPO_ROOT

MANUSCRIPT = REPO_ROOT / "publication" / "Naeem_final_clean_cardiac_CT_readability.docx"

# These tests need BOTH the manuscript and the parser that reads it. The parser lives
# on the working branch only, since it must not travel with a journal submission, and
# the manuscript sits in gitignored publication/. Checking only for the manuscript
# left the tests erroring on the reproduction branch instead of skipping, because the
# import failed inside the fixture rather than at collection.
_HAS_PARSER = importlib.util.find_spec("src.manuscript") is not None
pytestmark = pytest.mark.skipif(
    not (MANUSCRIPT.exists() and _HAS_PARSER),
    reason="needs the manuscript (gitignored) and src.manuscript (working branch only)",
)

LABEL_RE = re.compile(r"^(e?(?:Table|Figure) \d+)(?:\s*\([^)]*\))?\.\s+\S")
REFERENCE_RANGE = range(1, 26)


@pytest.fixture(scope="module")
def paragraphs() -> list[str]:
    import docx

    from src.manuscript import paragraph_texts

    return paragraph_texts(docx.Document(str(MANUSCRIPT)))


@pytest.fixture(scope="module")
def body(paragraphs) -> str:
    """Everything before the reference list.

    The split matters: the reference list is full of digits that look exactly like
    citation markers, and counting them as citations makes every reference appear
    cited.
    """
    idx = next(i for i, p in enumerate(paragraphs) if p.strip() == "References")
    return " ".join(paragraphs[:idx])


@pytest.fixture(scope="module")
def defined_labels(paragraphs) -> set[str]:
    """Displays that have a legend, i.e. that actually exist."""
    return {m.group(1) for p in paragraphs for m in [LABEL_RE.match(p.strip())] if m}


def _cited_labels(body: str) -> set[str]:
    """Display labels referenced in the text, singular or plural.

    Authors write "Figure 1", but also "eFigures 5, 4, and 6" and "Figures 1 and 2".
    A matcher that only understands the singular form reports perfectly good
    citations as missing, which is how this helper first failed.
    """
    found: set[str] = set()
    for m in re.finditer(r"\b(e?)(Table|Figure)s?\s*(\d+(?:[\s,]*(?:and\s+)?\d+)*)", body):
        prefix, kind, numbers = m.group(1), m.group(2), m.group(3)
        for num in re.findall(r"\d+", numbers):
            found.add(f"{prefix}{kind} {num}")
    return found


def _cited_references(body: str) -> set[int]:
    found = set()
    for group in re.findall(r"(?<=[a-zA-Z\)\.,])(\d{1,2}(?:[,–-]\d{1,2})*)(?=[\s\.,;:\)]|$)", body):
        for part in re.split(r"[,–-]", group):
            if part.isdigit() and int(part) in REFERENCE_RANGE:
                found.add(int(part))
    return found


# --- display numbering -------------------------------------------------------

def test_display_labels_are_sequential_without_gaps(defined_labels):
    """Figure 1, 2, 3 ... with nothing skipped and nothing repeated.

    A renumbering pass that misses one occurrence shows up here as a gap.
    """
    for prefix in ("Table", "Figure", "eTable", "eFigure"):
        nums = sorted(int(x.split()[1]) for x in defined_labels
                      if x.split()[0] == prefix)
        if not nums:
            continue
        assert nums == list(range(1, len(nums) + 1)), (
            f"{prefix} numbering is not contiguous: {nums}")
        assert len(nums) == len(set(nums)), f"duplicate {prefix} number in {nums}"


def test_main_displays_are_within_the_journal_limit(defined_labels):
    """JAMA allows five tables and figures combined for this article type.

    Supplementary displays carry an 'e' prefix and do not count, which is precisely
    why the prefix has to be right.
    """
    main = [x for x in defined_labels if not x.startswith("e")]
    assert len(main) <= 5, f"{len(main)} main displays exceeds the limit of 5: {sorted(main)}"


def test_front_matter_display_counts_match_the_document(paragraphs, defined_labels):
    """The title page must not claim a count the document contradicts."""
    front = " ".join(paragraphs[:25])
    n_tables = len([x for x in defined_labels if x.startswith("Table")])
    n_figures = len([x for x in defined_labels if x.startswith("Figure")])
    m = re.search(r"Tables:\s*(\d+)", front)
    if m:
        assert int(m.group(1)) == n_tables, (
            f"front matter says {m.group(1)} tables; document defines {n_tables}")
    m = re.search(r"Figures:\s*(\d+)", front)
    if m:
        assert int(m.group(1)) == n_figures, (
            f"front matter says {m.group(1)} figures; document defines {n_figures}")


# --- cross-references --------------------------------------------------------

def test_every_in_text_reference_resolves_to_a_real_display(body, defined_labels):
    """A reference to a display that does not exist is a dead pointer for the reader."""
    dangling = _cited_labels(body) - defined_labels
    assert not dangling, f"referenced but never defined: {sorted(dangling)}"


def test_every_display_is_called_out_in_the_text(body, defined_labels):
    """A display no sentence points to has no reason to be in the paper.

    A main figure was uncited at one point in this project's history, which is
    exactly the kind of omission a reviewer notices before the authors do.
    """
    uncited = defined_labels - _cited_labels(body)
    assert not uncited, f"defined but never cited in the text: {sorted(uncited)}"


# --- references --------------------------------------------------------------

def test_no_citation_points_past_the_reference_list(body):
    numbers = _cited_references(body)
    assert not {n for n in numbers if n > 25}, "citation numbered beyond the reference list"


def test_uncited_references_are_few_and_known(body):
    """Every listed reference should ideally be cited.

    A small number remain uncited pending an editorial decision about where they
    belong; this test pins that number so the backlog cannot silently grow.
    """
    uncited = sorted(set(REFERENCE_RANGE) - _cited_references(body))
    assert len(uncited) <= 2, f"uncited references grew to {len(uncited)}: {uncited}"


# --- numeric presentation ----------------------------------------------------

def test_no_p_value_is_printed_as_zero(paragraphs):
    """'P = .00' claims an impossibility.

    This appeared twice, produced by a formatter that rounded 0.0023 to two decimals.
    A P value below .01 needs more digits, or the '< .001' form.
    """
    text = " ".join(paragraphs)
    assert not re.findall(r"P\s*[=<]\s*\.00(?!\d)", text), "a P value is printed as .00"


def test_no_placeholder_text_remains(paragraphs):
    """Catch template scaffolding before a reviewer does."""
    text = " ".join(paragraphs)
    for token in ("[insert", "TBD", "XXX", "@@", "TODO", "FIXME", "Lorem ipsum"):
        assert token not in text, f"placeholder {token!r} left in the manuscript"


def test_no_doubled_display_prefix(paragraphs):
    """Guards a real bug: renaming 'Figure 1' inside 'eFigure 1' produced 'eeFigure 1'."""
    text = " ".join(paragraphs)
    assert "eeFigure" not in text and "eeTable" not in text


# --- manifest agreement ------------------------------------------------------

def test_display_manifest_matches_the_manuscript(defined_labels):
    """The manifest drives the submission bundle, so a disagreement ships the wrong file."""
    import yaml

    manifest = yaml.safe_load((CONFIG_DIR / "displays.yaml").read_text())
    declared = {item["label"]
                for group in ("main_figures", "supplementary_figures",
                              "main_tables", "supplementary_tables")
                for item in manifest[group]}
    assert declared == defined_labels, (
        f"manifest and manuscript disagree; "
        f"only in manifest: {sorted(declared - defined_labels)}, "
        f"only in manuscript: {sorted(defined_labels - declared)}")
