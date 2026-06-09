# Reviewer Guide — Blinded Clinical Accuracy Scoring (Aim 3)

**For:** Dr. Muhammad Naeem (subspecialist reviewer)
**Prepared by:** the data-science pipeline, 2026-06-09
**Your task in one line:** score each AI-rewritten patient page against its original on three 1–5 scales, blinded to which AI model wrote it.

This guide tells you exactly what was done before you, what you need to do, and what happens after. Please read §5 (Blinding) before you start — it is the part that protects the integrity of the result.

---

## 1. What this study is

We measured the reading level of 26 online patient-education pages for three pre-procedure cardiac-CT use cases (coronary CTA, TAVR planning, LAAO planning), then used three frontier large language models (LLMs) to rewrite each page at a 6th-grade reading level. The open question your review answers is the one that matters clinically:

> When an AI lowers the reading level of a patient page, does it keep the medicine correct and complete, or does it introduce errors and omissions?

Your blinded scoring is the **primary** evidence for that question (Aim 3). Reading level (Aim 1/2) is already done by formula; **you are scoring medical content only.**

## 2. What has already been done (so you have the full picture)

| Aim | Status | Result |
|-----|--------|--------|
| 1. Reading level of the 26 original pages | Done | 0/26 met the 6th-grade benchmark; median Flesch–Kincaid Grade Level 10.3 |
| 2. Reading-level effect of AI rewriting | Done | All 3 models dropped grade level by 3.9–5.7; two of three met the benchmark on ~80% of pages |
| 3. **Medical accuracy of the rewrites** | **Your task** | — |

There are **77 rewrites** to score (26 pages × 3 models, minus 1 rewrite that one model's content filter truncated and we excluded).

**An automated pre-screen exists, and you should NOT look at it yet.** To prioritize effort and to later validate the automation, a panel of three LLMs also scored every rewrite on the same rubric. Those automated scores are deliberately **kept out of this packet** so they cannot anchor your judgment. After you return your scores, we compare human vs automated agreement; your scores are the reference standard, not theirs.

## 3. Your packet

You receive one file:

- **`data/review/review_packet_with_text.csv`** — one row per rewrite, self-contained. Columns:
  - `blind_id` — opaque ID (e.g., `B-7QK2…`). **The only identifier. It does not encode the model.**
  - `original_text` — the full original patient page.
  - `rewrite_text` — the full AI rewrite to score.
  - `accuracy_1_5`, `completeness_1_5`, `added_errors_1_5` — **you fill these in.**
  - `notes` — **you fill this in** for any flagged row (see §4).

Open it in Excel or Google Sheets. The rows are in a randomized order (seeded), so models are interleaved unpredictably. Score top to bottom; do not try to guess the model.

## 4. The rubric (score each rewrite on all three, integers 1–5)

The full rubric is in [`docs/accuracy_scoring_rubric.md`](accuracy_scoring_rubric.md); the anchors are reproduced here so you can score from this one document.

**Accuracy** — are all medical statements correct?
`5` all accurate · `4` one minor inaccuracy (no change to understanding) · `3` one moderate inaccuracy (could confuse, not harm) · `2` multiple inaccuracies or one that could drive a wrong decision · `1` major inaccuracies likely to cause harm or refusal of care.

**Completeness** — did the rewrite keep the key prep, risk, and safety points of the original?
`5` all key points present · `4` all major points, one minor dropped · `3` one major point dropped · `2` multiple major points dropped · `1` omits most prep/risk/safety info.

**Added errors** — did the rewrite invent claims not in the original? **(higher = worse)**
`1` nothing invented · `2` one trivial added claim · `3` one non-trivial added medical claim · `4` multiple added claims or one clearly wrong invented claim · `5` substantial fabricated content.

**Notes:** for any row scored **≤ 3 on accuracy or completeness, or ≥ 3 on added errors**, write a one-line note naming the specific problem (e.g., "says contrast is iodine-free — wrong" or "dropped the 45-day anticoagulation instruction"). These notes become the qualitative backbone of the manuscript.

Score **only medical content** — not tone, not reading level, not formatting. If style bothers you, put it in `notes`, not in the numbers.

## 5. Blinding integrity (please follow exactly)

- You never see the model name; the `blind_id` does not encode it.
- Do not open `data/review/blind_key.csv` (it maps `blind_id` → model and is held by the data scientist).
- Do not look at the automated LLM scores (`data/scores/accuracy_llm*.csv`) until after you submit — they would anchor you.
- Score each rewrite against its own original only; do not compare rewrites to each other.

## 6. How to return your work and what happens next

1. Save the filled `review_packet_with_text.csv` (keep the `blind_id` column intact) and send it back.
2. The data scientist joins your scores to `blind_key.csv` on `blind_id` to un-blind, producing `data/scores/accuracy.csv` (the **primary** Aim 3 dataset).
3. `scripts/07_run_statistics.py` then produces the Aim 3 tables/figures: per-model accuracy/completeness/added-errors, the reading-level-vs-accuracy trade-off, and the across-model comparison.
4. We compute human-vs-automated agreement (weighted κ / correlation) to report how trustworthy the automated screen was — a result of independent methodological interest.
5. If a second subspecialist can score even a 15–20 page subset, we compute inter-rater κ; this materially strengthens the paper.

## 7. Time estimate

77 rewrites at ~3–5 minutes each ≈ **4–6 hours**, ideally in 2–3 sittings to avoid fatigue. If your time is tight, tell us and we can hand you a pre-registered random subset (e.g., 13 pages × 3 models = 39) and treat the rest as a second wave.

## 8. Questions

Anything ambiguous in the rubric, contact the data scientist before scoring rather than guessing — consistency matters more than speed. Thank you; this single step is what turns a reading-level descriptive study into a clinically actionable one.
