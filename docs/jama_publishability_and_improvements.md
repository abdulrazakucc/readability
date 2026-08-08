# JAMA Publishability Assessment + Improvements + Alternative Statistical Tests

A frank assessment for the cardiac CT readability + AI rewrite study (project root: `readability/`) of (1) whether this work, as currently scoped and powered, is realistically a JAMA-flagship paper, (2) what the more realistic top-tier journal homes are, (3) concrete methodological improvements that would lift the work toward those venues, and (4) alternative statistical tests to consider for each aim.

## TL;DR

1. **JAMA flagship is unlikely with the current scope.** Sample size (n = 21 included pages), single-procedure-area focus (cardiac CT), single-reader clinical scoring, and absence of a downstream clinical outcome make this a tough sell at *JAMA* (general medicine; major clinical impact threshold). It is not impossible, JAMA has published readability + AI-in-medicine adjacent work, but the path requires meaningful scope expansion.
2. **Realistic top-tier targets, ranked.** *JAMA Cardiology*; *JAMA Network Open*; *Journal of the American College of Cardiology (JACC)*; *JACC: Cardiovascular Imaging*; *Radiology*; *European Heart Journal, Imaging Methods and Practice* (where Piersson 2025 lives); *Patient Education and Counseling*; *JMIR Medical Informatics* / *JMIR Medical Education*.
3. **The single biggest improvement** is to *finish Aims 2 and 3* with a multi-reader blinded clinical-accuracy design, that is the methodological novelty the field needs, and it is the difference between a confirmatory readability replication (decent) and a primary-data contribution on the LLM-rewriting–accuracy trade-off (publishable at JAMA-family or specialty top-tier).
4. **The current statistical plan is sound**; alternative tests below address robustness, effect-size reporting, and reviewer-anticipated objections rather than fixing a defect.

## 1. Realistic journal targets

### 1.1 Why JAMA flagship is a stretch

The JAMA family publishes a small number of patient-education / AI-in-medicine papers, but at the flagship *JAMA* tier they typically share at least one of:

- A randomized clinical trial design with patient-level outcomes.
- Large multi-institutional samples (n in the thousands).
- A clear policy or care-pathway implication that a general internist will recognize.
- An author group with mature track records in either health-services research or clinical AI evaluation.

This study, as currently scoped:
- Is observational and cross-sectional.
- Has n = 21 patient education pages.
- Targets a procedural-imaging niche (pre-procedure cardiac CT, three use cases).
- Will measure subspecialist-rated AI rewrite accuracy on those 21 pages × 3 models, with a single primary reviewer in the base plan.

The headline "0/21 pages meet the 6th-grade benchmark" is intuitive and important, but it is one more replication of an established finding in a small subdomain. The headline *would-be* novelty, the LLM rewriting–accuracy trade-off, is exactly the kind of contribution top general journals are increasingly interested in, but the current scale and single-reader design make it specialty rather than general.

### 1.2 The realistic ranked list

| Rank | Target journal | Why it fits | What it would still want |
|---:|---|---|---|
| 1 | **JAMA Cardiology** | Cardiology-specialty home of JAMA family; routinely publishes patient-education and AI-evaluation studies in cardiology. | Aims 2 & 3 complete; PEMAT or equivalent comprehension measure; multi-reader κ; sample expansion. |
| 2 | **JAMA Network Open** | Lower threshold than JAMA flagship; explicitly broad and quantitative; happy with cross-sectional design + AI methods. | Aims 2 & 3 complete; clean reproducibility statement; preregistration. |
| 3 | **JACC** / **JACC Cardiovascular Imaging** | Specialty cardiology / imaging audience; receptive to imaging-procedure–specific patient-education work. | Aims 2 & 3 complete; imaging-specific Discussion framing. |
| 4 | **Radiology** | Strongest fit for the imaging methodology and the patient-education angle in radiology. | Reframe Introduction/Discussion to foreground the radiology-imaging angle of CCTA / TAVR planning CT / LAAO CT. |
| 5 | **European Heart Journal, Imaging Methods and Practice** | Direct fit (Piersson 2025 is the immediate predecessor); editor likely receptive to a cardiac-CT companion. | Less prestigious than 1–4 but a high-probability acceptance once Aims 2 & 3 complete. |
| 6 | **Patient Education and Counseling** | Patient-education home; publishes both readability surveys and AI-rewriting studies. | Less cardiology-focused framing in Discussion. |
| 7 | **JMIR Medical Informatics** / **JMIR Medical Education** / **npj Digital Medicine** | AI-in-medicine specialty homes; receptive to LLM-rewriting evaluation. | Aim 3 framing as a digital-health intervention evaluation. |

### 1.3 Two paths to JAMA flagship

If the team specifically wants to target *JAMA*, the realistic scope-expansion paths are:

**Path A, Scale and multi-disease.** Expand the readability+rewriting design beyond cardiac CT to multiple cardiovascular procedures (e.g., add: TAVR + LAAO + CCTA + carotid stenting + PAD intervention + CIED implant + ablation). n on the order of 100–200 pages, balanced across procedures and sites. Same per-page Aim 2/3 methodology. Same blinded accuracy scoring but two readers throughout (not just on a subset) plus a meaningful inter-rater κ result. This gives JAMA enough breadth to call it "cardiovascular patient education" rather than "cardiac CT." Estimated effort: 6–12 months additional.

**Path B, Add a downstream clinical outcome.** Pilot deployment of the highest-performing LLM rewrite at one or two institutions, with a measured patient-comprehension outcome (e.g., teach-back rate post-consult) or a procedure-day knowledge quiz. This converts the study from "audit of readability and AI rewriting" to "interventional evaluation of AI-mediated patient education." This is the JAMA-RCT-level contribution. Estimated effort: 12–24 months, IRB review required.

If neither Path A nor Path B is feasible, **target JAMA Cardiology or JAMA Network Open** rather than the flagship; both will accept the current scope cleanly once Aims 2 and 3 complete and the improvements in §2 are in.

## 2. Concrete improvements (ordered by impact-to-effort)

### High-impact, low-to-moderate effort

1. **Add PEMAT (understandability + actionability) as a co-primary outcome alongside FKGL.** Formula-based readability is what the field defaults to but it is widely understood to be incomplete. PEMAT-P (printable materials version) gives an orthogonal measure of how learnable the material is. AHRQ provides the standardized scoresheet; two raters can score 21 pages in a few hours. PEMAT is also the most common reviewer-requested addition for this kind of study. **Largest single quality lift for the least effort.**

2. **Add a second blinded clinical reviewer for the Aim 3 accuracy scoring on the full sample, not just a subset.** With two reviewers throughout: report Cohen's weighted κ per dimension as a primary result, and report mean of reviewers per page as the analysis input. Single-reviewer designs are an automatic reviewer objection; the planned two-reviewer-subset design is *acceptable* at specialty journals but *insufficient* at the JAMA tier.

3. **Recover the 5 blocked Hopkins / Mayo pages** (currently excluded with HTTP 403). Manual capture in a browser, paste body text, re-run cleaning and scoring. Brings n from 21 to 26 and recovers two of the largest U.S. academic-medical-center patient portals. Logged in `docs/stats_deviations.md`.

4. **OSF or equivalent independent pre-registration.** The git history is already a tamper-evident pre-registration but an OSF (or ClinicalTrials.gov, less likely applicable here) registration is the form a JAMA-family reviewer will look for. Mirror the statistical analysis plan + prompt + model lock + site allowlist to OSF before running Phase 3 of the pipeline. Submit screenshot of OSF page with the manuscript.

5. **Add at least one open-weight model to the rewrite arm panel** (e.g., Llama 3.x 70B Instruct, Qwen 2.5 72B Instruct, or DeepSeek V3). Without an open-weight comparator the rewrite arm is entirely proprietary-API; with one, you can address the reviewer comment "what about open-source alternatives?" up front.

6. **Reasoning-tier model as a stretch arm.** Add one frontier reasoning model (e.g., Claude with extended thinking, GPT with reasoning mode, Gemini "Deep") as a separate analysis to test whether reasoning-tier models trade differently on the readability-vs-accuracy curve. Treat as exploratory secondary analysis to avoid inflating multiple-comparison correction.

### High-impact, higher effort

7. **Multi-reviewer comprehension testing in real patients.** Recruit a small cohort (n = 30–50) of cardiac-patient volunteers; show them random original-vs-rewrite pairs (blinded); measure comprehension via a brief quiz. Even a small pilot dataset moves the contribution from "we measured numbers on a page" to "we measured what patients actually understand."

8. **Expand sample to ~50–100 pages across ≥ 5 cardiovascular procedures (Path A in §1.3).**

### Lower-impact but worth doing

9. **Sensitivity analyses to log in the manuscript Methods:**
  - Re-run all primary analyses excluding pages with residual site-chrome flagged at QA.
  - Re-run all primary analyses dropping the two longest-tail pages (RadiologyInfo TAVR at 16.36, BWH CTA at 15.58) to test outlier sensitivity.
  - Re-run with cleaned-text recomputed using `readability` (Python wrapper for Mozilla Readability) as an alternative extractor; cross-validate against the trafilatura primary.

10. **Pin the cleaner config in a versioned artifact, not just by source-code lock.** Emit a `cleaner_config_v1.json` next to each cleaned file so a reviewer can re-derive the cleaned text without running the Python code.

11. **Report effect sizes with confidence intervals for all primary comparisons**, not just p-values. Specifically: Cohen's d_z for paired t; rank-biserial r for Wilcoxon; ε² or η² for Kruskal-Wallis / Friedman; Spearman ρ with 95% bootstrap CI. The current SAP already requires most of these; verify the implementation in `scripts/07_run_statistics.py` produces them.

12. **Add a per-model token-usage and cost table** to the supplement. Reviewers and editors are increasingly asking how reproducible LLM-based studies are at the cost level. The data is already captured in the rewrite provenance files; surfacing it as a table costs almost nothing and shows methodological seriousness.

13. **Reporting checklists in the supplement.** STROBE (cross-sectional), MI-CLAIM (AI modeling), and a brief CHEERS-equivalent statement for cost reporting. JAMA-family submission portals ask for these explicitly.

### Things *not* to do

- **Do not** post-hoc widen the FKGL benchmark (e.g., "FKGL ≤ 8 also represents a clinically reasonable bar"). The 6th-grade benchmark is the pre-registered primary; moving it after seeing the data is a fishing maneuver that any seasoned reviewer will catch.
- **Do not** drop pages from analysis after seeing the scores. Every excluded page must have a pre-registered exclusion reason logged before the score was looked at.
- **Do not** add a fourth model panel mid-study, even a tempting one, without locking it as a new pre-registration entry. If a new model (e.g., Opus 4.8, Gemini 3 Deep) arrives mid-study, run it as a separate locked secondary analysis with its own pre-registration and report it as such.

## 3. Alternative statistical tests to consider

The current SAP in `docs/statistical_analysis_plan.md` is methodologically sound. The alternatives below are not *replacements* but *additions or robustness checks* that strengthen the reviewer response.

### 3.1 Aim 1, Reading level of original pages

**Currently planned:** descriptive (mean ± SD, median IQR); ANOVA / Kruskal–Wallis across sites and procedures; proportion meeting FKGL ≤ 6.

**Alternatives worth adding or substituting:**

| Alternative | What it adds | When to use it |
|---|---|---|
| One-sample Wilcoxon signed-rank against H₀: median = 6.0 | Direct, formula-free test of the headline "do these pages meet the benchmark?" | Use as the primary inferential test on the benchmark question alongside the descriptive 0/21 proportion. |
| Clopper–Pearson exact 95% CI on the meeting-benchmark proportion | Honest CI on the 0/21 (or k/n) headline. | Always, already added in the draft Results. |
| Permutation test on between-site / between-procedure mean differences | Distribution-free; robust to the small n; doesn't depend on Kruskal–Wallis large-sample approximation. | Use as the primary inferential when n per group is small (LAAO has n = 5). |
| Mixed-effects model with site as random intercept | Accounts for clustering of pages within sites. With n = 21 across 7–8 sites it is data-limited, but the framework is the right one if the sample grows. | Use in the Path A expansion (50–100 pages) where clustering is statistically tractable. |
| Bayesian estimation (e.g., BEST: Bayesian estimation supersedes the t-test) | Posterior on the difference, credible intervals; no dichotomous p-value. | Add as a robustness-check supplement; cite Kruschke 2013. |
| Tolerance-interval analysis on FKGL | "What FKGL range covers 95% of pages with 95% confidence?", answers a practical question editors like. | Add to supplement; small effort. |

**Recommended primary upgrade for Aim 1:** add the one-sample Wilcoxon vs the benchmark and the Clopper–Pearson exact CI as primary outputs alongside the descriptive table. Add the permutation test as the robustness check for the small-n between-group comparisons.

### 3.2 Aim 2, Effect of AI rewriting on reading level (paired, per model)

**Currently planned:** paired t-test or Wilcoxon signed-rank per (formula × model); Holm–Bonferroni across the 18 comparisons; Cohen's d_z / rank-biserial r effect size.

**Alternatives worth adding or substituting:**

| Alternative | What it adds | When to use it |
|---|---|---|
| Equivalence (TOST) test on Δ FKGL against a clinically meaningful equivalence bound (e.g., Δ FKGL > −1) | Lets you make claims like "this model failed to lower reading level by at least one grade." | Important if some models show small, statistically significant deltas that are not clinically meaningful. |
| Linear mixed-effects model: `score ~ condition * model + (1 | page_id)` | Single model handles all three rewrites + original in one framework; produces direct contrasts; doesn't require 18 separate paired tests. | Recommended as the *primary* Aim 2 model if the team is comfortable with mixed-effects; the per-model paired tests then become marginal effects from this model. |
| Bayesian paired model (e.g., BRMS) with informative priors centered at Δ = 0 | Posterior on each model's Δ; no multiple-comparison problem in the frequentist sense. | Add as robustness or as a supplementary preferred analysis if reviewers prefer Bayesian. |
| Bootstrap-based 95% CI on Δ instead of t-based CI | Robust to non-normality at n ≈ 21–26. | Always include alongside the t-based CI. |
| Per-page proportion of formulas (out of 6) showing a meaningful Δ | A "consilience" outcome: how often does the model lower most of the six scores at once? | Useful supplement; emphasizes that the six formulas correlate, which a reviewer will ask about. |

**Recommended primary upgrade for Aim 2:** add the mixed-effects model as the primary or co-primary analysis; keep the per-model paired tests as the now-marginal-effects view; add the TOST equivalence test against a pre-specified meaningful Δ bound.

### 3.3 Aim 3, Reading-level / accuracy trade-off

**Currently planned:** Spearman correlation of per-page Δ FKGL against accuracy (1–5) per model; Friedman test for model comparison on each clinical dimension; Cohen's weighted κ on a subset.

**Alternatives worth adding or substituting:**

| Alternative | What it adds | When to use it |
|---|---|---|
| Generalized additive model (GAM): `accuracy ~ s(Δ FKGL) + model + (1 | page_id)` | Detects nonlinear trade-off (e.g., accuracy fine for small Δ, falls off a cliff at larger Δ). | Useful if the scatter looks nonlinear; the small n limits power but the shape is interpretable. |
| Ordinal logistic regression with `accuracy` as ordered factor: `accuracy ~ Δ FKGL + model + (1 | page_id)` | Correctly treats accuracy as ordinal; gives an interpretable odds ratio per unit Δ FKGL. | Recommended primary modeling tool for the trade-off; more defensible than Spearman alone. |
| Bivariate latent-variable model jointly modeling reading-level drop and accuracy | Treats both as imperfect measures of underlying constructs. | Probably overkill at n = 21; consider for the Path A expansion. |
| Concordance / discordance analysis (Somers' D, Kendall's τ) | Alternative ordinal association measure with different sensitivity to ties. | Add to the supplement to demonstrate robustness across rank-correlation measures. |
| Multi-rater agreement: Gwet's AC2 instead of (or alongside) Cohen's weighted κ | More robust to the high-base-rate-agreement problem κ has when most scores are 4 or 5. | If the accuracy distribution is concentrated at the high end (common for rewrites that don't hallucinate), Gwet's AC2 is a more honest agreement measure than κ. |
| Confusion-matrix-style category accuracy if the 1–5 scale is collapsed to a 2-category "acceptable / unacceptable" | Provides a binary safety statistic editors find compelling. | Pre-register the collapsing rule before scoring; do not collapse post-hoc. |

**Recommended primary upgrade for Aim 3:** swap the Spearman primary for an ordinal mixed-effects model with page as a random intercept; keep Spearman as a supplement. Add Gwet's AC2 alongside Cohen's κ for inter-rater reliability. Pre-register a binary "acceptable / unacceptable" collapsing rule for a secondary safety analysis.

### 3.4 Multiple-comparison correction philosophy

The current plan uses Holm–Bonferroni across the 18 Aim 2 paired tests. Two alternatives:

| Approach | Trade-off |
|---|---|
| Holm–Bonferroni (current) | Strong family-wise error control; conservative; standard. Stick with this as the primary. |
| Benjamini–Hochberg FDR | Less conservative; controls false-discovery rate not family-wise. Often preferred for exploratory analyses across many comparisons. Add as a supplement. |
| Hierarchical Bayesian shrinkage | No "correction" needed in the frequentist sense; partial-pooling shrinks per-model estimates toward each other. Most defensible methodologically but adds modeling complexity. |

Stick with Holm–Bonferroni as primary. Mention BH-FDR robustness in the methods footnote.

## 4. What this checklist would look like in priority order, given current state

If the team has 4–6 weeks before submission:

1. Unblock API keys and run Phase 3 (rewrites). Run Phase 4 (blinded clinical scoring).
2. Recover the 5 Hopkins/Mayo pages manually (improvement #3).
3. Recruit a second clinical reviewer; have them score the full Aim 3 sample, not just a subset (improvement #2).
4. Add PEMAT scoring of originals + best-performing model rewrite to the manuscript as a co-primary measure (improvement #1).
5. Add the mixed-effects model for Aim 2 and ordinal mixed-effects model for Aim 3 to `scripts/07_run_statistics.py` (alternative tests §3.2 and §3.3).
6. OSF pre-registration of the locked SAP + prompt + model panel (improvement #4).
7. Run all sensitivity analyses (improvement #9).
8. Submit to **JAMA Cardiology** or **JAMA Network Open**. Hold *JAMA* flagship as a stretch target only with a successful Path-A or Path-B expansion (a separate, larger study).

If the team has 6–12 months and the budget for it:

1. All of the above.
2. Expand sample to ~80–120 pages across five cardiovascular procedures (Path A).
3. Add an open-weight model and a reasoning-tier model to the panel (improvements #5 and #6).
4. Pilot the comprehension-testing arm in real patients (improvement #7), separate IRB application.
5. Reassess venue based on results; *JAMA Cardiology* becomes high-confidence, *JAMA* flagship becomes a realistic stretch.
