# IRB submission package

Materials for the institutional review of the human-reviewer component of the study
*Readability of Online Patient-Education Materials for Pre-Procedure Cardiac CT*.

## Contents

| File | What it is |
|---|---|
| `cardiac_readability_IRB_proposal.docx` | Protocol submitted for review |
| `cardiac_readability_supporting_documents.docx` | Supporting documentation |
| `Cardiac_Readability_IRB_Attachments.html` | Attachment set |
| `Preparation_Notes_and_Decisions.docx` | Preparation notes |
| `instruments/` | The review instrument as administered, in Word and PDF |

## The review instrument

Reviewers scored one of two presentation variants of the same instrument. Both are
included because the distinction is material to the ethical review:

- **`Review_Instrument_labeled`** — names the two passages *Original page* and
  *AI rewrite*.
- **`Review_Instrument_neutral`** — identical items, identical order, identical
  scales, but the wording never indicates which passage is machine-generated. This
  variant exists so that some reviewers scored without that knowledge.

Each contains the cover sheet, reviewer instructions, the three 1–5 scoring scales
with their definitions, and all 77 paired passages exactly as administered.

## How these documents are produced

`scripts/22_build_irb_instruments.py` renders them from
`data/review/blinded_review_packet_with_text.csv` — the same committed packet the
reviewers actually scored. Nothing is retyped, so the submitted instrument cannot
drift from what was administered. Re-run the script after any change to the packet.

## Participant confidentiality

The instrument records a **participant ID only**; no reviewer name appears anywhere
in these documents. Score sheets are stored under opaque IDs (`E01`–`E06` for
subspecialist reviewers, `L01`–`L05` for lay reviewers). The single file mapping IDs
to names is held outside version control with the study's ethics records.
