# Methods, Metrics, and Statistics: A Plain-Language Companion

**Who this is for.** Dr. Naeem and any clinician co-author who wants to understand exactly what every number in the manuscript means, and any data scientist or student who wants to follow or re-implement the project end to end. It assumes no statistics background. Where a test or metric is named in the manuscript, this document explains it in words, shows the formula, and works a small example using the project's own data.

**How to read it.** Sections 1 to 3 are the conceptual orientation (the question, the metrics, the pipeline). Section 4 is the statistics, one test at a time, each with a worked example. Section 5 covers the automated LLM-judge panel (the secondary Aim 3 analysis). Section 6 is a plain-language glossary. Section 7 is the reproduction map: which script produces which number. A clinician can read 1 to 3 and the glossary and skip the arithmetic; an implementer can read the whole thing.

**A note on honesty of numbers.** Every figure quoted below was read directly from the committed CSVs in `reports/` and `data/scores/` on the n = 26 corpus. None are invented for illustration. Where a worked example uses made-up small numbers to show a calculation, it says so explicitly.

---

## 1. The study in three sentences

We measured how hard to read the online patient-education pages for three pre-procedure cardiac CT topics are (coronary CT angiography, TAVR planning, and LAAO/Watchman), across the major US and UK hospital and society websites. We then asked three frontier AI chatbots to rewrite each page at a lower reading level and measured how far the reading level dropped. Finally we asked whether that simplification costs medical accuracy, which is the question that decides whether such rewriting is safe to put in front of patients.

These map to the three Aims:

- **Aim 1** (descriptive): how readable are the original pages, and do any meet the recommended 6th-grade level?
- **Aim 2** (the rewrite effect): does each AI model lower the reading level, and by how much?
- **Aim 3** (the trade-off): does lowering the reading level cost medical accuracy or completeness? The primary measure here is a blinded subspecialist review (Dr. Naeem); a secondary automated LLM-judge panel is reported as a screening signal only.

---

## 2. The readability metrics: six formulas

Readability formulas estimate how hard a passage is to read from surface features of the text: how long the sentences are, and how long or syllable-heavy the words are. They do **not** understand meaning. A sentence can be perfectly readable by formula and still be medically wrong; that is exactly why Aim 3 (human accuracy review) exists alongside Aim 1/2 (formula scores).

We report six formulas because the field reports all six, and using one alone invites the criticism that the result is a quirk of that formula. They mostly agree. All are computed by the `textstat` Python library, and we record the exact `textstat` version with every score so a future re-run on a different version is detectable (see `src/readability.py`).

| Formula | What it returns | Direction | Inputs it uses |
|---|---|---|---|
| **FKGL** Flesch-Kincaid Grade Level | A US school grade (e.g., 8.0 = 8th grade) | Lower = easier | words/sentence, syllables/word |
| **FKRE** Flesch Reading Ease | A 0 to 100 score (100 = very easy) | **Higher = easier** | words/sentence, syllables/word |
| **GFI** Gunning Fog Index | A US grade | Lower = easier | words/sentence, % "complex" (3+ syllable) words |
| **SMOG** Simple Measure of Gobbledygook | A US grade | Lower = easier | count of polysyllabic words per 30 sentences |
| **CLI** Coleman-Liau Index | A US grade | Lower = easier | characters/word, sentences/word (no syllables) |
| **ARI** Automated Readability Index | A US grade | Lower = easier | characters/word, words/sentence |

**FKGL is our headline metric** because the benchmark we test against is stated in grades. The US National Library of Medicine and the American Medical Association recommend patient materials be written at or below a **6th-grade level**, so the project's pass/fail test is **FKGL ≤ 6**.

### 2.1 Worked example: the Flesch-Kincaid Grade Level formula

FKGL is defined as:

```
FKGL = 0.39 × (total words / total sentences)
     + 11.8 × (total syllables / total words)
     − 15.59
```

Read it as: longer sentences push the grade up, and more syllables per word push it up harder (the 11.8 weight is large). Take a short illustrative passage (made-up, for arithmetic):

> "The scan uses a special dye. The dye helps the doctor see your heart."

That is 2 sentences, 14 words, and roughly 16 syllables (the/scan/u-ses/a/spe-cial/dye/the/dye/helps/the/doc-tor/see/your/heart). Plugging in:

```
FKGL = 0.39 × (14 / 2) + 11.8 × (16 / 14) − 15.59
     = 0.39 × 7        + 11.8 × 1.143     − 15.59
     = 2.73            + 13.49            − 15.59
     ≈ 0.6
```

So this very plain passage scores about a 1st-grade level. Now contrast a real clinical sentence:

> "Coronary computed tomography angiography requires intravenous administration of iodinated contrast material, which carries a small risk of nephropathy in patients with pre-existing renal impairment."

That is 1 sentence, 24 words, and many 4-to-6 syllable words (com-pu-ted, an-gi-o-gra-phy, in-tra-ve-nous, ad-min-i-stra-tion, i-o-din-a-ted, neph-rop-a-thy). With ~58 syllables:

```
FKGL = 0.39 × (24 / 1) + 11.8 × (58 / 24) − 15.59
     = 9.36            + 28.52            − 15.59
     ≈ 22
```

A grade of 22 is far past any school grade; it signals "this is graduate/specialist prose." This single contrast is the whole project in miniature: the same medical fact can be told at grade 1 or grade 22, and the formulas detect the difference.

### 2.2 What the originals actually scored (Aim 1 result)

On the 26 original pages, read from `reports/aim1_descriptives_overall.csv`:

| Metric | Mean | SD | Median |
|---|---:|---:|---:|
| FKGL | 10.5 | 2.5 | 10.3 |
| FKRE | 50.7 | 12.1 | 54.0 |
| GFI | 13.7 | 2.6 | 13.1 |
| SMOG | 13.1 | 1.8 | 12.7 |
| CLI | 11.5 | 1.9 | 11.2 |
| ARI | 11.4 | 2.9 | 11.0 |

The median page reads at **grade 10.3** (mid-high-school), with an interquartile range of 8.7 to 11.9. **0 of 26 pages met FKGL ≤ 6** (`reports/aim1_benchmark_meeting.csv`). Every formula agrees the pages sit well above the 6th-grade target.

---

## 3. The pipeline (how the numbers are produced)

The whole analysis is a chain of numbered, re-runnable scripts. Each reads the previous step's output and writes a new file; nothing is edited by hand. This is what makes every number in the manuscript reproducible from the raw HTML.

```
data/urls.csv
  → 01_capture_pages   raw HTML saved with capture time, HTTP status, content hash
  → 02_clean_pages     strip nav/ads/captions/references → body-only text
  → 03_score_originals → data/scores/originals.csv        (Aim 1 inputs)
  → 04_generate_rewrites  one rewrite per page per model  (Aim 2 inputs)
  → 05_score_rewrites  → data/scores/rewrites.csv, deltas.csv
  → 06_build_review_packet  blinded, shuffled packet for the human reviewer
  → 07_run_statistics  → reports/aim1_*, aim2_*    (the locked inferential tests)
  → 08_generate_figures → reports/figures/aim1_*, aim2_*
  → 09_llm_accuracy    automated 3-judge panel     (Aim 3 secondary)
  → 10_aim3_llm_stats  → reports/aim3_llm_*
  → 11_aim3_llm_figures → reports/figures/aim3_llm_*
```

Three reproducibility rules govern the chain (full version in `docs/implementation_guidelines.md`):

1. **Raw is immutable.** `data/raw/` is never edited after capture. The 5 pages that blocked automated capture (Hopkins x3, Mayo x2) were recovered by manual browser paste and that fact is recorded in their provenance and in `docs/stats_deviations.md`; the corpus is n = 26.
2. **One prompt, three models.** Every model gets the identical rewrite prompt (`prompts/rewrite_v1.txt`). A per-page prompt tweak would bias the cross-model comparison, so it is forbidden; any prompt change gets a new version and a deviation-log entry.
3. **Two-way blinding for Aim 3.** The clinical reviewer never sees which model wrote a rewrite (each is given a random `blind_id`), and the data scientist never sees the clinical scores during data prep. The unblinding key (`data/review/blind_key.csv`) is kept out of the reviewer's packet.

---

## 4. The statistics, one test at a time

This section explains every test named in the manuscript Methods. The unifying idea: we have measurements, and we want to know whether a difference we see (a lower reading level after rewriting, a gap between sites) is **real** or could plausibly be **chance**. A statistical test turns that question into a number, the **p-value**.

### 4.0 The two ideas you need first

**p-value.** The probability of seeing a difference at least as large as the one observed *if there were truly no effect*. Small p (by convention **p < 0.05**) means "chance alone is an unlikely explanation, so we treat the effect as real." p is **not** the probability the result is true, and it says nothing about how *big* or *important* the effect is. That is what effect sizes and confidence intervals are for.

**Parametric vs non-parametric.** Parametric tests (t-test, ANOVA) assume the data follow a roughly bell-shaped (normal) distribution. Non-parametric tests (Wilcoxon, Kruskal-Wallis, Friedman, Spearman) make no such assumption and work on ranks instead of raw values; they are safer for small samples and skewed or ordinal data, at a small cost in power when the data really are normal. Our pipeline **chooses automatically per outcome**: it runs a normality check and uses the parametric test only when it is justified, otherwise the non-parametric one. This is the right behavior for a study with n = 26 and a mix of continuous (readability) and ordinal (1 to 5 accuracy) outcomes.

### 4.1 Describing the data: mean, SD, median, IQR

Before any test, we summarize. Two pairs of summaries appear throughout:

- **Mean ± SD.** The mean is the average; the standard deviation (SD) is the typical distance of a value from that average. Good when the data are roughly symmetric. Example: FKGL mean 10.5, SD 2.5 means "the average page is grade 10.5, and most pages fall roughly within 10.5 ± 2.5, i.e., grade 8 to 13."
- **Median (IQR).** The median is the middle value (half the pages are above, half below); the interquartile range (IQR) is the 25th to 75th percentile, i.e., the middle half of the pages. Robust to outliers, which is why we report it alongside the mean. Example: FKGL median 10.3, IQR 8.7 to 11.9.

Reporting both lets a reader see skew: when mean and median are close (10.5 vs 10.3 here), the distribution is roughly symmetric.

### 4.2 Checking assumptions: Shapiro-Wilk and Levene

Two gatekeeper tests decide which main test runs. They are run silently inside `src/stats.py`; you do not see their numbers in the manuscript, but they determine which test name appears.

- **Shapiro-Wilk** tests whether a sample is consistent with a normal (bell-curve) distribution. If its **p > 0.05** we keep the normal assumption (the data look bell-shaped enough). The code uses this to pick a t-test/ANOVA vs the rank-based alternative (`_is_approx_normal` in `src/stats.py`).
- **Levene's test** checks whether two or more groups have roughly equal spread (variance). ANOVA assumes they do. If Levene's **p > 0.05**, variances are close enough.

**Decision rule actually coded for Aim 1:** use ANOVA only if *all* groups pass Shapiro-Wilk *and* Levene passes; otherwise use Kruskal-Wallis. You can see this play out in `reports/aim1_inference_by_procedure.csv`, where FKGL got `anova` (assumptions held) but FKRE got `kruskal` (they did not).

### 4.3 Aim 1 inferential: ANOVA vs Kruskal-Wallis

**Question:** do reading scores differ across the websites, or across the three procedures?

- **One-way ANOVA** (analysis of variance) asks whether several groups have different means, using the ratio of between-group spread to within-group spread (the F statistic). Big F, small p means the groups really differ.
- **Kruskal-Wallis** is the rank-based equivalent for when normality/variance assumptions fail. It pools all values, ranks them, and asks whether some groups hold systematically higher ranks. Its statistic is reported as H (a chi-square-distributed value).

**Results actually obtained:**

- *Across procedures* (CTA vs TAVR vs LAAO): no significant difference on any formula. FKGL by ANOVA gave F = 0.06, **p = 0.94** (`reports/aim1_inference_by_procedure.csv`). Plain reading: the topic does not predict reading level; all three procedures' pages are uniformly hard.
- *Across sites:* FKGL by Kruskal-Wallis gave H = 15.7, **p = 0.074** (`reports/aim1_inference_by_site.csv`), i.e., borderline, not significant at 0.05. The spread is wide in practice: Mayo Clinic averaged FKGL 8.0 (the most readable) and Brigham and Women's Hospital 15.1 (the least), but with only 2 to 4 pages per site the omnibus test cannot certify the gap. Post-hoc pairwise tests are run only if the omnibus test is significant, so none were run here.

This is an honest null-ish result and is reported as such. It does not weaken the headline Aim 1 finding (0/26 meet the benchmark), which is a simple count, not a between-group test.

### 4.4 Aim 2 core: the paired test (did rewriting lower the grade?)

**Question:** for each model, is a page's reading level lower *after* rewriting than before?

The key word is **paired**: every rewrite is compared to *its own* original, page by page, so each page is its own control. We analyze the **delta** (post minus pre) for each page. A negative delta on FKGL means the grade dropped (good).

- **Paired t-test** is used when the per-page deltas are approximately normal (Shapiro-Wilk on the deltas). It tests whether the mean delta differs from zero.
- **Wilcoxon signed-rank test** is the rank-based fallback when the deltas are not normal.

For each test we report: n pairs, mean delta, a **95% confidence interval** on the delta, the raw p, the Holm-adjusted p (see 4.5), and an **effect size**.

**Confidence interval (CI).** The 95% CI is the range that would contain the true mean delta 95% of the time under repeated sampling. A CI that does not include 0 means the effect is statistically distinguishable from "no change." It also shows the *magnitude* plainly, which a p-value hides.

**Effect size.** Tells you how big the change is in standardized units, independent of sample size:
- **Cohen's dz** (for the paired t-test) = mean delta ÷ SD of the deltas. By convention 0.2 is small, 0.5 medium, 0.8 large. Our FKGL effects are around 2.2 to 2.8, which is enormous.
- **Rank-biserial r** (for Wilcoxon) plays the same role on the rank scale.

**Results actually obtained** (FKGL, from `reports/aim2_paired_tests.csv`; all three used the paired t-test because the deltas were normal):

| Model | n | Mean ΔFKGL | 95% CI | Cohen's dz | Holm-adjusted p | Pages reaching ≤ 6 |
|---|---:|---:|---|---:|---:|---:|
| Claude Opus 4.8 | 26 | −5.52 | [−6.32, −4.71] | −2.77 | 2.8 × 10⁻¹² | 22 / 26 |
| Gemini 3.1 Pro | 26 | −5.74 | [−6.60, −4.88] | −2.70 | 4.0 × 10⁻¹² | 20 / 26 |
| GPT-5.5 | 25 | −3.90 | [−4.64, −3.17] | −2.18 | 5.2 × 10⁻¹⁰ | 9 / 25 |

Every model lowered the grade by a large, highly significant margin. Claude and Gemini each brought roughly 80% of pages to the 6th-grade target that *none* of the originals met; GPT-5.5 simplified less aggressively. (GPT-5.5 has n = 25 because one rewrite was excluded after its content filter truncated it; see `docs/stats_deviations.md`.)

### 4.5 Holm-Bonferroni: the multiple-comparisons correction

**The problem.** If you run many tests at p < 0.05, you expect some "significant" results by chance alone (run 20 tests on pure noise and on average 1 looks significant). Aim 2 runs 6 formulas × 3 models = **18 paired tests**, so a correction is required.

**The fix.** Holm-Bonferroni sorts the 18 raw p-values from smallest to largest and applies a progressively less strict threshold to each, controlling the chance of *any* false positive across the whole family. It is uniformly stricter than no correction but less conservative (more powerful) than the classic Bonferroni. We report **both** the raw and the Holm-adjusted p so reviewers can see the correction's effect. In our case the effects are so strong that every comparison survives correction by many orders of magnitude (see the table above).

### 4.6 Friedman test: comparing the three models head-to-head

**Question:** do the three models differ from *each other* in how low they push the reading level (not just each vs its own original)?

The **Friedman test** is the non-parametric way to compare three or more matched conditions measured on the same subjects. Here each page contributes three post-rewrite FKGL values (one per model), the test ranks the three within each page, and asks whether one model systematically ranks lower. It is the repeated-measures cousin of Kruskal-Wallis and yields a chi-square statistic.

**Result:** for post-rewrite FKGL, **χ² = 38.0, p = 5.6 × 10⁻⁹** (n = 25 pages with all three rewrites, `reports/aim2_across_models.csv`). The models do differ: Claude and Gemini are comparable to each other and both push lower than GPT-5.5. The test uses **listwise deletion** (a page must have all three rewrites to enter), which is why n = 25, not 26.

### 4.7 Aim 3 primary: the human accuracy review (pending)

The **primary** Aim 3 endpoint is Dr. Naeem's blinded scoring of all 77 rewrites on three 1-to-5 ordinal dimensions defined in `docs/accuracy_scoring_rubric.md`:

- **Accuracy** (5 = every medical statement correct; 1 = major errors likely to harm).
- **Completeness** (5 = all key prep/risk/safety points kept; 1 = most omitted).
- **Added errors**, reverse-coded (1 = nothing invented; 5 = substantial fabrication). Higher is worse on this one axis; the analysis flips it so all three face the same direction in figures.

When those human scores return, three pre-registered analyses run (the code already exists in `src/stats.py`):

- **Spearman correlation** between each page's reading-level drop (ΔFKGL) and its accuracy score, per model. Spearman is a rank correlation (ρ, from −1 to +1) that needs no normality and suits ordinal scores. A **negative ρ** would be the headline trade-off: "the more a model simplified, the less accurate it became." We report ρ, a bootstrap 95% CI (5,000 resamples), and p.
- **Friedman test** across the three models on each clinical dimension (same machinery as 4.6), with Holm-corrected Wilcoxon post-hoc if significant.
- **Cohen's weighted kappa** if a second reader scores a subset, to quantify inter-rater agreement (see 5.5).

This is the measurement that actually answers the deploy/do-not-deploy question, and it is why no automated score is allowed to stand in for it.

---

## 5. The automated LLM-judge panel (Aim 3 secondary)

Because the human review takes time, we built a **secondary, clearly-labeled** screening analysis: a panel of three LLM judges (the same three models) scored all 77 rewrites against their originals on the same three rubric dimensions, each judge blinded to which model wrote the rewrite. That is 77 rewrites × 3 judges = **231 judgments** (`data/scores/accuracy_llm_raw.csv`). This is a triage and validation tool, **not** a substitute for Dr. Naeem; the manuscript states this in every place the panel appears, and full detail is in `docs/aim3_automated_accuracy_assessment.md`.

### 5.1 Consensus score

For each rewrite, the **consensus** is the mean of the three judges' scores on each dimension (`data/scores/accuracy_llm.csv`). Averaging independent raters reduces the noise of any one judge.

### 5.2 The trade-off finding

Per-model consensus means (`reports/aim3_llm_descriptives.csv`), shown against the Aim 2 reading-level reduction:

| Model | Reading-level reduction (mean ΔFKGL) | Accuracy (1-5) | Completeness (1-5) | Added errors (1-5, lower better) |
|---|---:|---:|---:|---:|
| GPT-5.5 | −3.90 (smallest) | **5.00** | **4.95** | **1.07** (best) |
| Claude Opus 4.8 | −5.52 | 4.91 | 4.91 | 1.18 |
| Gemini 3.1 Pro | −5.74 (largest) | 4.69 | 4.81 | 1.45 (worst) |

The ordering is the **inverse** of the reading-level ordering: the most aggressive simplifier (Gemini) scored lowest on accuracy, the most conservative (GPT-5.5) highest, and Claude occupied the favorable corner (near-largest simplification with near-top fidelity). Across-model accuracy differed significantly by Friedman (**χ² = 21.1, p = 2.6 × 10⁻⁵**, n = 25); completeness (χ² = 5.57, p = 0.062) and added errors (χ² = 5.02, p = 0.081) did not reach significance. This is visualized two ways: a per-page scatter (`aim3_llm_tradeoff.png`) and a dual-axis model summary (`aim3_llm_tradeoff_alt.png`).

### 5.3 The ceiling effect (read this before trusting the panel)

**88.7%** of the 231 accuracy judgments were the maximum score of 5, and no rewrite received the lowest score (1) on accuracy or completeness (`data/scores/accuracy_llm_raw.csv`). When almost everything piles up at the top of the scale, that is a **ceiling effect**. It has two consequences the manuscript states plainly: (a) gross fabrication was genuinely rare across all models, which is reassuring; but (b) the scale has little room to discriminate, so rank-based agreement statistics look weak even when the judges substantively agree (see next).

### 5.4 Inter-judge agreement: three numbers, because each tells half the story

Reported in `reports/aim3_llm_interjudge.csv`:

- **Mean pairwise Spearman** (rank agreement): accuracy 0.26, completeness 0.49, added errors 0.53. These look modest.
- **Kendall's W** (coefficient of concordance, 0 to 1, computed from the Friedman statistic as W = χ² / [n(k−1)]): 0.09 to 0.20. Also modest.
- **Within-1-point agreement** (fraction of rewrites where the judges' highest and lowest scores differ by ≤ 1): accuracy 0.96, completeness 0.99, added errors 0.90.

The apparent contradiction (low rank agreement but very high absolute agreement) is the **signature of the ceiling effect**: when 88.7% of scores are a 5, there is almost no variance for a rank correlation to latch onto, so Spearman collapses toward 0 even though the judges almost always land within a point of each other. Reporting all three numbers, and explaining why they diverge, is the honest way to present this; quoting only Spearman would understate agreement and quoting only within-1-point would overstate it.

### 5.5 Cohen's weighted kappa (for the human second reader)

For the *human* review, agreement between two readers on an ordinal 1-to-5 scale is measured with **Cohen's weighted kappa**, not plain percent-agreement, because kappa subtracts out the agreement expected by chance, and the *weighting* (linear or quadratic) counts a 4-vs-5 disagreement as much milder than a 1-vs-5 disagreement. Convention: kappa < 0.4 is poor, 0.4 to 0.6 moderate, 0.6 to 0.8 good. If kappa is poor on any dimension, the readers reconcile by discussion before the final analysis. This applies to Aim 3 primary only if a second reader scores a subset.

### 5.6 Self-preference: did any judge favor its own work?

A panel of LLM judges that also produced the rewrites invites an obvious bias: a model might score its own output generously. We tested this directly with a **Mann-Whitney U test** (a non-parametric test of whether one group's values tend to be larger than another's) comparing each judge's scores on its *own* rewrites vs *other* models' rewrites (`reports/aim3_llm_self_preference.csv`).

One judge showed it clearly: the **GPT-5.5 judge scored its own rewrites 5.00 on accuracy vs 4.64 for others (p = 0.001)**. The Claude judge (+0.04, p = 0.51) and the Gemini judge (−0.21, p = 0.07; if anything it scored its own *lower*) did not show favoritism. This both tempers GPT-5.5's apparent accuracy advantage in 5.2 and is a concrete, reproducible reason the manuscript insists the human review is primary. Detecting this bias is *why* the panel uses all three models as judges rather than one.

---

## 6. Glossary (alphabetical, plain language)

- **ANOVA:** test for a difference in means across 3+ groups (assumes normal data). Aim 1.
- **Bootstrap:** estimating a confidence interval by re-sampling the data many times (here 5,000) and watching how much the statistic moves. Used for the Aim 3 Spearman CI.
- **Ceiling effect:** most scores pile at the top of the scale, leaving little room to discriminate. Affects the LLM panel's accuracy axis.
- **Cohen's dz:** paired effect size = mean change ÷ SD of the change. 0.2/0.5/0.8 = small/medium/large.
- **Confidence interval (95%):** the plausible range for the true value; if it excludes 0 (for a difference), the effect is statistically real.
- **Effect size:** how *big* an effect is, in standardized units, independent of sample size. Complements the p-value, which only says whether an effect is *detectable*.
- **FKGL:** Flesch-Kincaid Grade Level, our headline readability metric; the target is ≤ 6.
- **Friedman test:** non-parametric comparison of 3+ matched conditions on the same subjects (each page rewritten by each model). Aim 2 and Aim 3 model comparisons.
- **Holm-Bonferroni:** a stepwise correction that controls false positives when many tests are run together. Applied to the 18 Aim 2 paired tests.
- **IQR (interquartile range):** the middle 50% of values (25th to 75th percentile). Robust summary of spread.
- **Kendall's W:** agreement among 3+ raters, 0 (none) to 1 (perfect). Inter-judge agreement.
- **Kruskal-Wallis:** non-parametric ANOVA; compares 3+ groups by ranks. Aim 1 fallback.
- **Levene's test:** checks whether groups have equal spread; gatekeeper for ANOVA.
- **Mann-Whitney U:** non-parametric test of whether one group's values tend to exceed another's. Used for the self-preference check.
- **Mean ± SD:** average and typical deviation from it. Best for symmetric data.
- **Median:** the middle value; half above, half below. Robust to outliers.
- **Non-parametric:** makes no bell-curve assumption; works on ranks. Safer for small or ordinal data.
- **p-value:** probability of the observed (or more extreme) result if there were truly no effect. p < 0.05 is the threshold for "treat as real." Not the probability of being right, not a measure of size.
- **Paired test:** compares each item to itself under two conditions (page before vs after rewriting), removing between-page variability.
- **Parametric:** assumes a known distribution (usually normal); more powerful when the assumption holds.
- **Rank-biserial r:** effect size companion to the Wilcoxon test.
- **Shapiro-Wilk:** tests whether data are consistent with a normal distribution; gatekeeper for parametric tests.
- **Spearman correlation (ρ):** rank-based correlation, −1 to +1; no normality needed. The Aim 3 trade-off statistic.
- **Weighted kappa (Cohen's):** chance-corrected agreement between two raters on an ordinal scale, with near-misses penalized less than far-misses. The human inter-rater metric.
- **Wilcoxon signed-rank test:** non-parametric paired test; the fallback for the paired t-test.

---

## 7. Reproduction map: which script makes which number

Every number in the manuscript can be traced to a script and a CSV. To regenerate everything from the raw HTML:

```bash
.venv/bin/python scripts/03_score_originals.py --included-only   # originals.csv
.venv/bin/python scripts/05_score_rewrites.py                    # rewrites.csv, deltas.csv
.venv/bin/python scripts/07_run_statistics.py                    # reports/aim1_*, aim2_*
.venv/bin/python scripts/08_generate_figures.py                  # reports/figures/aim1_*, aim2_*
.venv/bin/python scripts/09_llm_accuracy.py --aggregate          # accuracy_llm*.csv  (Aim 3 secondary)
.venv/bin/python scripts/10_aim3_llm_stats.py                    # reports/aim3_llm_*
.venv/bin/python scripts/11_aim3_llm_figures.py                  # reports/figures/aim3_llm_*
```

| Manuscript claim | Source file | Test / metric (this doc) |
|---|---|---|
| Median FKGL 10.3 (IQR 8.7-11.9); 0/26 meet ≤ 6 | `reports/aim1_descriptives_overall.csv`, `aim1_benchmark_meeting.csv` | §4.1, §2.2 |
| No procedure difference (FKGL ANOVA p = 0.94) | `reports/aim1_inference_by_procedure.csv` | §4.3 |
| Site difference borderline (FKGL KW p = 0.074); Mayo 8.0, BWH 15.1 | `reports/aim1_inference_by_site.csv`, `aim1_descriptives_by_site.csv` | §4.3 |
| Per-model ΔFKGL, CI, dz, % reaching ≤ 6 | `reports/aim2_paired_tests.csv`, `data/scores/rewrites.csv` | §4.4, §4.5 |
| Models differ post-rewrite (FKGL Friedman χ² = 38.0) | `reports/aim2_across_models.csv` | §4.6 |
| Automated panel consensus means; Friedman χ² = 21.1 | `reports/aim3_llm_descriptives.csv`, `aim3_llm_model_comparison.csv` | §5.2 |
| Ceiling: 88.7% accuracy at 5 | `data/scores/accuracy_llm_raw.csv` | §5.3 |
| Inter-judge agreement (Spearman / Kendall W / within-1) | `reports/aim3_llm_interjudge.csv` | §5.4 |
| Self-preference (GPT-5.5 own 5.00 vs 4.64, p = 0.001) | `reports/aim3_llm_self_preference.csv` | §5.6 |

The test logic lives in `src/stats.py` (locked at Phase 5). The readability formulas are in `src/readability.py`. The judge prompt and parser are in `src/llm_judge.py`. Any change to a locked test is recorded in `docs/stats_deviations.md`.

---

*Companion to the manuscript and to `docs/statistical_analysis_plan.md` (the pre-registered plan). For the rubric Dr. Naeem uses, see `docs/accuracy_scoring_rubric.md`; for step-by-step reviewer instructions, `docs/reviewer_guide_naeem.md`; for the automated-panel write-up, `docs/aim3_automated_accuracy_assessment.md`.*
