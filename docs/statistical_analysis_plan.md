# Statistical Analysis Plan (SAP)

**Status: pre-registered.** Lock this document with a git commit before running any inferential test on Phase 2 or later data. Any deviation goes in `docs/stats_deviations.md`.

## Significance threshold

α = 0.05, two-sided. No multiple-comparison correction at the family level *unless* we run >10 paired comparisons in Aim 2 — in that case apply Holm-Bonferroni and report both raw and adjusted p-values.

## Aim 1 — Reading level of original pages

**Question:** how do reading scores differ across websites and across procedures for the original (non-rewritten) pages?

### Descriptive

- Mean ± SD and median (IQR) for each of the six scores, overall.
- Same, stratified by site (n per cell ≥ 3 to report; otherwise pool).
- Same, stratified by procedure.
- Count and proportion of pages meeting the 6th-grade benchmark (FKGL ≤ 6).

### Inferential

For each readability score, test for differences across websites:
- If the score is approximately normal (Shapiro-Wilk p > 0.05 AND visual QQ plot is straight) AND variances are roughly homogeneous (Levene p > 0.05): **one-way ANOVA**.
- Otherwise: **Kruskal-Wallis**.

Repeat the test for differences across procedures.

Post-hoc only if the omnibus test is significant. Use Tukey HSD for ANOVA or Dunn's test for Kruskal-Wallis.

## Aim 2 — Does AI rewriting lower the reading level?

**Question:** for each model, does the rewritten page have a lower (better) reading level than the original?

### Per-model paired comparison

For each of the six scores × each of the three models:

- If paired differences are approximately normal: **paired t-test**.
- Otherwise: **Wilcoxon signed-rank test**.

Total tests: 6 scores × 3 models = 18 paired comparisons. **Apply Holm-Bonferroni** across these 18.

Report:
- n pairs
- Mean (or median) delta
- 95% CI on the delta
- Raw p
- Holm-adjusted p
- Effect size (Cohen's dz for paired t; rank-biserial r for Wilcoxon)

### Across-model comparison

For each readability score, test whether the three models differ in their post-rewrite scores:

- If parametric: **repeated-measures ANOVA** with model as the within-subject factor (each page contributes three rewritten scores).
- Otherwise: **Friedman test**.

If significant, post-hoc pairwise comparisons with Holm-Bonferroni.

## Aim 3 — Accuracy vs reading-level trade-off

**Question:** does dropping reading level cost medical accuracy or completeness?

### Descriptives

- Mean ± SD of accuracy, completeness, and added-errors scores per model.
- If two readers: Cohen's weighted kappa per dimension.

### Trade-off analysis

For each model, correlate per-page reading-level drop (delta in FKGL) against the per-page accuracy and completeness scores:

- **Spearman correlation** (ordinal accuracy scores, no normality assumption).
- Report ρ, 95% CI (via bootstrap, 5000 resamples), and p.

A negative correlation (more reading-level drop ↔ lower accuracy) is the headline trade-off finding.

### Model comparison on clinical scores

For each clinical dimension, test for differences across models:
- **Friedman test** (ordinal, paired per page).
- Post-hoc Wilcoxon signed-rank with Holm-Bonferroni.

## Power and sample-size sanity check

With n=20–40 pages and 3 models, the paired tests have reasonable power for medium effects (Cohen's d ≈ 0.5) at α=0.05. Underpowered for small effects. State this honestly in the manuscript Discussion.

## Missing data

A rewrite may be missing if the model refused or errored. Policy:

- If <10% of cells missing per model: complete-case analysis, footnote the n.
- If ≥10% missing: investigate. Likely a prompt or model problem, not a statistical one.

## Outputs

`scripts/06_run_statistics.py` produces:

- `reports/aim1_descriptives.csv`
- `reports/aim1_inference.csv`
- `reports/aim2_paired_tests.csv`
- `reports/aim2_across_models.csv`
- `reports/aim3_clinical_descriptives.csv`
- `reports/aim3_tradeoff_correlations.csv`
- `reports/aim3_model_comparison.csv`
- `reports/figures/aim1_*.png`
- `reports/figures/aim2_*.png`
- `reports/figures/aim3_tradeoff.png`

Every CSV has a header row and a final row with the script git SHA + timestamp.

## What we will NOT do

- No fishing. No "let's also try this test and see if it's significant."
- No re-running with a different significance threshold post-hoc.
- No reporting unplanned subgroup analyses unless flagged as exploratory.
- No reading the p-values before the analysis script is finalized.

If the data forces a real deviation from this plan, the deviation is logged, dated, and reported in the manuscript Methods.
