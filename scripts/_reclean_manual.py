"""One-off: re-clean the 5 manually-captured pages to the pipeline standard.

These 5 pages returned HTTP 403 (bot detection) so they were captured by hand
in a browser. The pasted text still contained boilerplate that trafilatura would
normally strip (nav menus, related-link lists, promo/video sidebars, image
captions) and smart quotes / em dashes the sanitizer normally normalizes.

For each page we remove an explicit, auditable set of boilerplate lines, then run
the project's own normalizers (src.clean) so the result is consistent with the
other 16 auto-cleaned pages. We then regenerate the provenance JSON and report the
recomputed word_count for the manifest.
"""

from __future__ import annotations

from pathlib import Path

from src.clean import (
    _drop_junk_lines,
    _normalize_unicode,
    _normalize_whitespace,
    count_words,
    estimate_sentences,
)
from src.provenance import sha256_text, utc_now_iso, write_provenance

CLEANED = Path("data/cleaned")

# Boilerplate lines to drop, matched against the stripped line text.
DROP: dict[str, set[str]] = {
    "jhmi__cta__f15ba785": set(),  # already clean; normalize only
    "mayo__cta__7756ee3c": {
        "Products & Services",
        "A Book: Mayo Clinic Family Health Book",
        "Newsletter: Mayo Clinic Health Letter — Digital Edition",
        "Show fewer products from Mayo Clinic",
        "More Information",
        "Carotid artery disease",
        "Claudication",
        "Coarctation of the aorta",
        "Show more related information",
        "Request an appointment",
        "Clinical trials",
        "Explore Mayo Clinic studies of tests and procedures to help prevent, detect, treat or manage conditions.",
    },
    "mayo__tavr__739229dd": {
        "Hide transcript",
        "for video What is TAVR?",
        "Advanced heart surgery options",
        "For generations patients with heart conditions have turned to Mayo Clinic or answers, offering the full spectrum of specialized care and treatment options.",
        "Patients are surrounded by a team of heart experts to develop the strongest individualized treatment plans to provide the safest and most successful surgeries.",
        "There are many ways to reach the heart for surgery. During traditional heart surgery, the surgeons open the chest to access the heart. With advancing technologies, minimally invasive robotic surgery options are now available to treat a variety of heart conditions. During minimally invasive surgery, the heart is reached through tiny chest incisions.",
        "The surgical team at Mayo Clinic will recommend a unique care plan for each individual patient for best results focused on long-term outcomes. Together we are creating the future of heart care, one patient at a time.",
        "Catheter access sites in transcatheter aortic valve replacement",
        "Possible catheter access sites in transcatheter aortic valve replacement",
        "Enlarge image",
        "Clinical trials",
        "Explore Mayo Clinic studies of tests and procedures to help prevent, detect, treat or manage conditions.",
    },
    "jhmi__tavr__7bdb4834": {
        "TAVR Treatment at Johns Hopkins",
        "Heart disease specialists oversee your care.",
        "Treatments informed by latest research.",
        "Offered in Baltimore and Bethesda, Maryland.",
        "Structural Heart Disease Clinic",
        "couple watching video while preparing a meal",
    },
    "jhmi__laao__b5350128": {
        "Atrial Fibrillation (AFib) | Q&A with Dr. Hugh Calkins",
        "Diagram of the heart with the WATCHMAN device inserted into the left atrial appendage",
    },
}


def main() -> None:
    print(f"{'page_id':28} {'words':>6} {'sents':>6}")
    for page_id, drop in DROP.items():
        path = CLEANED / f"{page_id}.txt"
        raw = path.read_text(encoding="utf-8")

        # 1. Explicit boilerplate removal (match on stripped text, drop em-dash
        #    variants before/after unicode normalization).
        kept = [
            line
            for line in raw.splitlines()
            if line.strip() not in drop
        ]
        text = "\n".join(kept)

        # 2. Project-standard normalization (same as the auto pipeline).
        text = _normalize_unicode(text)
        text = _drop_junk_lines(text)
        text = _normalize_whitespace(text)

        path.write_text(text, encoding="utf-8")

        wc = count_words(text)
        sc = estimate_sentences(text)
        write_provenance(
            CLEANED / f"{page_id}.provenance.json",
            {
                "page_id": page_id,
                "cleaned_at_utc": utc_now_iso(),
                "content_sha256": sha256_text(text),
                "word_count": wc,
                "sentence_count_estimate": sc,
                "sanitizer_version": "1.0",
                "capture_method": "manual_browser",
            },
        )
        print(f"{page_id:28} {wc:6d} {sc:6d}")


if __name__ == "__main__":
    main()
