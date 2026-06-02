# Accuracy Scoring Rubric (Aim 3)

Used by the clinical subspecialist (Naeem) — and a blinded second reader where possible — to score each AI rewrite against its original.

## Setup

The data scientist hands the reviewer a packet (`data/review/packet_<batch>.csv` plus a folder with the texts):

- One row per blinded rewrite.
- Columns: `blind_id`, `original_text_path`, `rewrite_text_path`, `accuracy_1_5`, `completeness_1_5`, `added_errors_1_5`, `notes`.
- The reviewer fills in the three score columns and any notes. They do NOT see the model identity.

The order of rewrites within a packet is randomized (seeded RNG). The original is presented alongside the rewrite for each row.

## Rubric

Score each rewrite on each of three 1–5 dimensions. Higher is better on all three (the "added errors" axis is **reverse-coded** at scoring time — see below).

### 1. Accuracy (1–5)

Are all medical statements in the rewrite correct?

| Score | Meaning                                                                              |
|-------|--------------------------------------------------------------------------------------|
| 5     | Every medical statement is accurate. No clinical misstatements.                      |
| 4     | One minor inaccuracy that would not change patient understanding or behavior.        |
| 3     | One moderate inaccuracy that could confuse a patient but not cause harm.             |
| 2     | Multiple inaccuracies OR one inaccuracy that could lead to a wrong patient decision. |
| 1     | Major inaccuracies likely to cause patient harm or refusal of needed care.           |

### 2. Completeness (1–5)

Did the rewrite preserve the key preparation, risk, and safety points from the original?

| Score | Meaning                                                                                 |
|-------|-----------------------------------------------------------------------------------------|
| 5     | All key prep, risk, and safety points from the original are present.                    |
| 4     | All major points present; one minor point dropped.                                      |
| 3     | One major point (prep step or risk) dropped.                                            |
| 2     | Multiple major points dropped; rewrite is materially less informative than original.    |
| 1     | Rewrite omits most prep/risk/safety information.                                        |

### 3. Added errors (1–5, REVERSE-CODED)

Did the rewrite invent medical claims not in the original?

Score 1–5 where **higher means MORE invented content** (worse). The analysis script flips this at compute time so all three dimensions face the same direction in figures.

| Score | Meaning                                                                          |
|-------|----------------------------------------------------------------------------------|
| 1     | Nothing invented; rewrite contains only content present in original.             |
| 2     | One trivial added claim (e.g., a generic wellness platitude).                    |
| 3     | One non-trivial added medical claim (e.g., a stat not in the original).          |
| 4     | Multiple added claims, OR one clearly wrong invented claim.                      |
| 5     | Substantial fabricated medical content (hallucination).                          |

## Notes column

For any score ≤ 3 on accuracy or completeness, OR ≥ 3 on added errors, jot a one-line note saying what specifically was wrong. These notes are gold for the manuscript's qualitative discussion.

## Blinding integrity

The reviewer never sees:

- The model name or any model-identifying string.
- The order in which models were called (the packet is shuffled with a seeded RNG).
- Other reviewers' scores until the data scientist joins them post-hoc.

The data scientist never sees the scored sheets until Naeem returns the entire packet.

## Inter-rater agreement (if a second reader scores a subset)

The data scientist computes Cohen's weighted kappa (linear or quadratic weights) per dimension on the overlap subset and reports it. If kappa < 0.4 on any dimension, the readers reconcile via discussion BEFORE the data scientist looks at the final stats.

## What this rubric is NOT

- Not a check on reading level (the formulas do that).
- Not a check on tone or style.
- Not a PEMAT replacement (PEMAT may be added later as an optional secondary measure — see plan §2).

If the reviewer wants to flag style or formatting issues, use the notes column. Do not let those concerns leak into the three numeric scores.
