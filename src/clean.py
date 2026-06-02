"""HTML -> body-only text cleaning for patient education pages.

Pipeline:
  1. Trafilatura main-content extraction (handles navigation, sidebars, ads).
  2. Custom sanitizer pass to strip residual junk that inflates readability scores:
       - Image captions and figure references
       - "See also", "Related links", "Share this" blocks
       - Reference / citation lists at the end
       - Leading/trailing whitespace, smart quotes, em dashes
  3. Normalize whitespace so sentence segmentation is well-defined.

This module is deterministic given the same input HTML.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import trafilatura

from .provenance import sha256_text, utc_now_iso, write_provenance

log = logging.getLogger(__name__)


# Patterns that commonly leak into extracted text and inflate scores.
JUNK_LINE_PATTERNS = [
    re.compile(r"^\s*Share (this|on)\b.*", re.I),
    re.compile(r"^\s*Print this page\s*$", re.I),
    re.compile(r"^\s*(See also|Related|Related links?|Read more|More information):?\s*$", re.I),
    re.compile(r"^\s*References?\s*:?\s*$", re.I),
    re.compile(r"^\s*Citations?\s*:?\s*$", re.I),
    re.compile(r"^\s*Sources?\s*:?\s*$", re.I),
    re.compile(r"^\s*Last (updated|reviewed)\s*:.*$", re.I),
    re.compile(r"^\s*Page last reviewed.*$", re.I),
    re.compile(r"^\s*Copyright\b.*$", re.I),
    re.compile(r"^\s*All rights reserved\b.*$", re.I),
    re.compile(r"^\s*Figure \d+[.:].*$", re.I),
    re.compile(r"^\s*Fig\.\s*\d+[.:].*$", re.I),
    re.compile(r"^\s*Image[: ].*$", re.I),
]

# Lines that look like reference list entries. We accept either form:
#   - starts with "1. " (or "12.") followed by author-looking text and a 4-digit year
#   - contains "et al." plus a 4-digit year
REFERENCE_LINE = re.compile(
    r"^\s*(?:\d+\.\s+[A-Z][^.]+\.\s+.*\b\d{4}\b.*|.*\bet\s+al\.\s.*\b\d{4}\b.*)$"
)


@dataclass
class CleaningResult:
    page_id: str
    cleaned_text: str
    word_count: int
    sentence_count_estimate: int
    cleaned_path: Path
    provenance_path: Path
    content_sha256: str
    sanitizer_version: str = "1.0"


def _normalize_unicode(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    # Smart quotes -> ASCII
    text = (
        text.replace("‘", "'")
        .replace("’", "'")
        .replace("“", '"')
        .replace("”", '"')
        .replace("–", "-")
        .replace("—", "-")
        .replace(" ", " ")
    )
    return text


def _drop_junk_lines(text: str) -> str:
    out_lines: list[str] = []
    seen_references_header = False
    for line in text.splitlines():
        stripped = line.strip()
        # Hard cut: everything after a "References:" / "Sources:" header gets dropped
        if not seen_references_header and re.match(
            r"^(References?|Sources?|Citations?|Bibliography)\s*:?\s*$", stripped, re.I
        ):
            seen_references_header = True
            continue
        if seen_references_header:
            # Drop until a non-reference-looking line of substantial length appears
            if REFERENCE_LINE.match(line) or len(stripped) < 30:
                continue
            else:
                # End of references block
                seen_references_header = False
        if any(p.match(line) for p in JUNK_LINE_PATTERNS):
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def _normalize_whitespace(text: str) -> str:
    # Collapse 3+ newlines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multi-space within a line
    text = re.sub(r"[ \t]+", " ", text)
    # Strip trailing spaces per line
    text = "\n".join(line.rstrip() for line in text.splitlines())
    return text.strip() + "\n"


def estimate_sentences(text: str) -> int:
    # Simple heuristic — for sanity, not for scoring
    return max(1, len(re.findall(r"[.!?]+(?:\s|$)", text)))


def count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def extract_main_text(html: str | bytes) -> str:
    extracted = trafilatura.extract(
        html if isinstance(html, str) else html.decode("utf-8", errors="replace"),
        include_comments=False,
        include_tables=False,
        favor_recall=False,
        include_links=False,
        include_formatting=False,
    )
    return extracted or ""


def clean(
    page_id: str,
    raw_html: str | bytes,
    cleaned_dir: Path,
) -> CleaningResult:
    main = extract_main_text(raw_html)
    main = _normalize_unicode(main)
    main = _drop_junk_lines(main)
    main = _normalize_whitespace(main)

    cleaned_path = cleaned_dir / f"{page_id}.txt"
    cleaned_path.write_text(main, encoding="utf-8")

    sha = sha256_text(main)
    prov_path = cleaned_dir / f"{page_id}.provenance.json"
    write_provenance(
        prov_path,
        {
            "page_id": page_id,
            "cleaned_at_utc": utc_now_iso(),
            "content_sha256": sha,
            "word_count": count_words(main),
            "sentence_count_estimate": estimate_sentences(main),
            "sanitizer_version": "1.0",
        },
    )

    return CleaningResult(
        page_id=page_id,
        cleaned_text=main,
        word_count=count_words(main),
        sentence_count_estimate=estimate_sentences(main),
        cleaned_path=cleaned_path,
        provenance_path=prov_path,
        content_sha256=sha,
    )
