# Literature Review, Reading Level of Online Patient Education, and LLM Rewriting in Cardiology

A working bibliography and synthesis for the manuscript in `publication/draft_manuscript.md`. Organized by topic, not by year. Sources already in `literature/` are starred (★). New sources are listed with PubMed-style citation plus a one-sentence relevance note; **anything that needs author-level verification of exact details is flagged "VERIFY"**, do not cite from this document without confirming the citation at PubMed or the publisher.

> **Author note (Abdul):** This is a working bibliography assembled in the model's context window, not a librarian-verified list. Treat it as a starting point and verify each citation (author list, journal, year, DOI/PMID) before quoting in the manuscript. The ★-flagged sources are the four that exist in `literature/` and are verified.

---

## 1. The reading-level-and-patient-education methodology

### 1.1 Foundational and methodological

- ★ **McEnteggart GE, Naeem M, Skierkowski D, Baird GL, Ahn SH, Soares GM.** Readability of online patient education materials related to IR. *J Vasc Interv Radiol.* 2015;26(8):1164–1168. doi:10.1016/j.jvir.2015.03.019. PMID 25935147.
  *The methodological backbone the present study extends to cardiac CT. Reported IR patient-page reading levels 9.0 (NLM) up to 15.0 (Wikipedia), all above the 6th-grade recommendation. Established the six-formula consensus approach.*

- ★ **Agency for Healthcare Research and Quality (AHRQ).** The Patient Education Materials Assessment Tool (PEMAT) and User's Guide. 2020. https://www.ahrq.gov/health-literacy/patient-education/pemat.html
  *Validated instrument for understandability and actionability. Complements formula-based readability but measures a different construct. **Not** included as a primary outcome in the current study, its absence is one of the main improvements flagged in `docs/jama_publishability_and_improvements.md`.*

- **Shoemaker SJ, Wolf MS, Brach C.** Development of the Patient Education Materials Assessment Tool (PEMAT): A new measure of understandability and actionability for print and audiovisual patient information. *Patient Educ Couns.* 2014;96(3):395–403. doi:10.1016/j.pec.2014.05.027. PMID 24973195. **VERIFY.**
  *Original validation paper for PEMAT. Cite if PEMAT is added in revision.*

- **Friedman DB, Hoffman-Goetz L.** A systematic review of readability and comprehension instruments used for print and web-based cancer information. *Health Educ Behav.* 2006;33(3):352–373. doi:10.1177/1090198105277329. PMID 16699125. **VERIFY.**
  *Background on formula-based readability methodology and its known limitations.*

- **Eltorai AEM, Ghanian S, Adams CA Jr, Born CT, Daniels AH.** Readability of patient education materials on the American Association for Surgery of Trauma website. *Arch Trauma Res.* 2014;3(2):e18161. **VERIFY.**
  *Representative recent application of the six-formula methodology to a specialty website. Cite as part of the field's broader pattern.*

### 1.2 Health literacy outcomes (why reading level matters)

- **Berkman ND, Sheridan SL, Donahue KE, Halpern DJ, Crotty K.** Low health literacy and health outcomes: an updated systematic review. *Ann Intern Med.* 2011;155(2):97–107. doi:10.7326/0003-4819-155-2-201107190-00005. PMID 21768583. **VERIFY.**
  *Canonical review linking low health literacy to worse outcomes including hospitalization, ED use, and mortality. Anchor citation for the introduction's "why this matters."*

- **Bostock S, Steptoe A.** Association between low functional health literacy and mortality in older adults: longitudinal cohort study. *BMJ.* 2012;344:e1602. doi:10.1136/bmj.e1602. PMID 22422872. **VERIFY.**
  *UK longitudinal cohort tying low health literacy to all-cause mortality in older adults, a population that overlaps with TAVR/LAAO candidates.*

- **Magnani JW, Mujahid MS, Aronow HD, et al.** Health literacy and cardiovascular disease: fundamental relevance to primary and secondary prevention: a scientific statement from the American Heart Association. *Circulation.* 2018;138(2):e48–e74. doi:10.1161/CIR.0000000000000579. PMID 29866648. **VERIFY.**
  *AHA scientific statement explicitly linking health literacy to cardiovascular outcomes. Strongest single citation for relevance of patient-facing materials in cardiology.*

---

## 2. Readability of patient education in cardiology and cardiac imaging

### 2.1 Cardiac imaging (directly adjacent)

- ★ **Piersson AD, et al.** Readability of patient education materials on cardiac magnetic resonance imaging. *Eur Heart J, Imaging Methods and Practice.* 2025;3(2):qyaf111. doi:10.1093/ehjimp/qyaf111. PMCID PMC12448386.
  *The closest methodological predecessor to the present study. Applied six-formula readability to cardiac MRI patient pages across five sites; found uniform failure to meet the 6th-grade benchmark. Present study extends this approach to cardiac CT.*

- **Patel S, et al.** Readability of online patient education materials for coronary computed tomography angiography. **VERIFY existence/citation.** *If found, would be the most direct prior comparator for the present CCTA subaim.*

### 2.2 Cardiac procedures (TAVR, AFib/LAAO, CCTA broader space)

- **Wang LW, Miller MJ, Schmitt MR, Wen FK.** Assessing readability formula differences with written health information materials: Application, results, and recommendations. *Res Social Adm Pharm.* 2013;9(5):503–516. **VERIFY.**
  *Methods background on cross-formula agreement.*

- **Halladay JR, et al. (multiple authors writing on health-literacy interventions in cardiology).** **VERIFY specific paper.**
  *Cite if you need an interventional anchor for "low literacy ⇒ adverse cardiac outcome."*

- *(Targeted PubMed search recommended)*, searches that should be run before manuscript submission:
  - `(("transcatheter aortic valve") OR TAVR OR TAVI) AND (readability OR "health literacy") AND (patient information OR patient education)`
  - `(LAAO OR Watchman OR "left atrial appendage closure") AND (readability OR "health literacy")`
  - `("coronary CT angiography" OR CCTA) AND (readability OR "health literacy")`
  *Any hit from these searches that the present study did not pre-empt should be cited in §4.2 Comparison to Prior Work of the manuscript.*

---

## 3. LLMs in patient education and patient-facing medical text

### 3.1 LLM readability of generated medical content

- ★ **Behers BJ, Vargas IA, Behers BM, Rosario MA, Wojtas CN, Deevers AC, Hamad KM.** Assessing the readability of patient education materials on cardiac catheterization from artificial intelligence chatbots: an observational cross-sectional study. *Cureus.* 2024;16(7):e63865. doi:10.7759/cureus.63865. PMID 39099896.
  *Closest prior work on AI chatbots in cardiology patient education. Important contrast: Behers measured chatbot *generation* readability (chatbot answers patient questions); the present study measures chatbot *rewriting* of existing pages with blinded subspecialist accuracy scoring, the latter has not been done in cardiology imaging to our knowledge.*

- **Ayers JW, Poliak A, Dredze M, et al.** Comparing physician and artificial intelligence chatbot responses to patient questions posted to a public social media forum. *JAMA Intern Med.* 2023;183(6):589–596. doi:10.1001/jamainternmed.2023.1838. PMID 37115527. **VERIFY.**
  *Landmark JAMA Internal Medicine paper showing ChatGPT-3.5 answers rated as higher quality and more empathetic than physician answers in a non-blinded comparison. Methodological precedent for AI vs reference comparison in patient-facing text. (Note: a different design from this study, Ayers used quality ratings, not readability + accuracy.)*

- **Lee P, Bubeck S, Petro J.** Benefits, limits, and risks of GPT-4 as an AI chatbot for medicine. *N Engl J Med.* 2023;388(13):1233–1239. doi:10.1056/NEJMsr2214184. PMID 36988602. **VERIFY.**
  *Influential NEJM perspective on GPT-4 in medical contexts. Anchor citation for general background on LLMs in medical text.*

- **Singhal K, Azizi S, Tu T, et al.** Large language models encode clinical knowledge. *Nature.* 2023;620(7972):172–180. doi:10.1038/s41586-023-06291-2. PMID 37438534. **VERIFY.**
  *Foundational Nature paper on Med-PaLM. Cite for general LLM-in-medicine background.*

### 3.2 LLM rewriting / simplification of patient material (most direct)

- **Jeblick K, Schachtner B, Dexl J, et al.** ChatGPT makes medicine easy to swallow: an exploratory case study on simplified radiology reports. *Eur Radiol.* 2024;34(5):2817–2825. doi:10.1007/s00330-023-10213-1. PMID 37794249. **VERIFY.**
  *Closest prior work on LLM simplification of *radiology-adjacent* patient-facing text. Cite as direct precedent for the present Aim 2.*

- **Wei T, Strain B, Roberts T, et al.** Use of large language models to translate medical text: opportunities and limitations. **VERIFY actual citation.**
  *Recent review on LLMs for patient-facing text reformulation. Cite if a clean review citation can be found.*

- **Yeo YH, Samaan JS, Ng WH, et al.** Assessing the performance of ChatGPT in answering questions regarding cirrhosis and hepatocellular carcinoma. *Clin Mol Hepatol.* 2023;29(3):721–732. doi:10.3350/cmh.2023.0089. **VERIFY.**
  *One of many specialty-specific evaluations of LLM patient-facing content. Cite if you want to make the point that the methodology has been applied across specialties but rarely combines readability + clinical accuracy with blinding.*

- *(Targeted search recommended)*, PubMed searches before submission:
  - `("large language model" OR ChatGPT OR Claude OR Gemini OR GPT-4) AND (readability OR "reading level" OR "patient education")`
  - `("large language model" OR ChatGPT OR Claude OR Gemini OR GPT-4) AND ("medical accuracy" OR "factual accuracy" OR hallucination) AND (patient OR cardiology)`

### 3.3 LLM medical accuracy / hallucination

- **Pan A, Musheyev D, Bockelman D, Loeb S, Kabarriti AE.** Assessment of artificial intelligence chatbot responses to top searched queries about cancer. *JAMA Oncol.* 2023;9(10):1437–1440. doi:10.1001/jamaoncol.2023.2947. PMID 37615960. **VERIFY.**
  *JAMA Oncology brief report on accuracy and readability of chatbot answers, a useful methodological cousin to the present Aim 2/3 design.*

- **Goodman RS, Patrinely JR, Stone CA Jr, et al.** Accuracy and reliability of chatbot responses to physician questions. *JAMA Netw Open.* 2023;6(10):e2336483. doi:10.1001/jamanetworkopen.2023.36483. PMID 37782507. **VERIFY.**
  *JAMA Network Open paper on accuracy of chatbot responses, useful for cite-cluster on LLM accuracy in medicine.*

---

## 4. Methodological references (statistical, reporting standards)

### 4.1 Reporting checklists used or relevant

- **von Elm E, Altman DG, Egger M, et al.** The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement: guidelines for reporting observational studies. *Lancet.* 2007;370(9596):1453–1457. doi:10.1016/S0140-6736(07)61602-X. PMID 18064739. **VERIFY.**
  *Cross-sectional reporting standard relevant to Aim 1.*

- **Norgeot B, Quer G, Beaulieu-Jones BK, et al.** Minimum information about clinical artificial intelligence modeling: the MI-CLAIM checklist. *Nat Med.* 2020;26(9):1320–1324. doi:10.1038/s41591-020-1041-y. PMID 32908275. **VERIFY.**
  *Reporting standard for clinical-AI studies; the present study's pre-registration, blinding, and provenance choices were designed to satisfy MI-CLAIM.*

- **Collins GS, Moons KGM, Dhiman P, et al.** TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ.* 2024;385:e078378. doi:10.1136/bmj-2023-078378. **VERIFY.**
  *Cite only if the manuscript adds a predictive component in revision.*

- **Cruz Rivera S, Liu X, Chan AW, et al. SPIRIT-AI and CONSORT-AI Working Group.** Guidelines for clinical trial protocols for interventions involving artificial intelligence: the SPIRIT-AI extension. *Nat Med.* 2020;26(9):1351–1363. doi:10.1038/s41591-020-1037-7. PMID 32908284. **VERIFY.**
  *Reporting standard for AI-intervention *trials*, not directly applicable here (this study is observational) but worth knowing for any follow-on RCT.*

### 4.2 Reading-formula validation / reliability

- **Wang LW, Miller MJ, Schmitt MR, Wen FK.** (See §2.2 above.) Cross-formula agreement and choice rationale.

- **Note for revision:** A reviewer for a top-tier journal may ask whether formula-based readability is the right metric. Pre-empt by either (a) adding PEMAT (see `docs/jama_publishability_and_improvements.md`), or (b) citing the field's consensus that formula-based readability is a necessary first-line screening even if insufficient by itself.

---

## 5. Synthesis, where this study fits

The literature converges on three settled findings and three open questions.

**Settled findings.**
1. *Patient education materials systematically fail the 6th-grade benchmark.* Replicated across specialties for at least two decades, most recently in cardiac MRI (Piersson 2025) and IR (McEnteggart 2015).
2. *Health literacy correlates with cardiovascular outcomes.* AHA scientific statement (Magnani 2018) and large epidemiologic cohorts.
3. *LLMs can produce patient-facing medical text at varied reading levels.* Behers 2024 in cardiac catheterization; Jeblick 2024 in radiology reports; multiple JAMA-family papers on accuracy of ChatGPT answers to patient questions.

**Open questions this study targets.**
1. *What is the reading-level baseline for pre-procedure cardiac CT specifically?* (Aim 1; closed by this study at n=21; should be extended.)
2. *Do LLMs rewrite existing patient pages at lower reading levels without sacrificing medical accuracy?* The closest prior work measured LLM generation, not rewriting; the present design with a single locked prompt + blinded subspecialist scoring of rewrite accuracy is, to our knowledge, a methodological first in cardiac imaging.
3. *What is the per-model trade-off curve between reading-level reduction and accuracy preservation?* This is the operational decision point for any health system considering AI-mediated patient education and is the central novelty claim of Aim 3.

The opportunity for a high-impact contribution is concentrated in Aims 2 and 3, not Aim 1. Aim 1 is a necessary baseline and a useful confirmatory replication in a new cardiology-imaging subdomain. Aims 2 and 3, executed cleanly with blinding and pre-registration, are the publishable headline.

---

## 6. Bibliography in `literature/citations.bib`

The following four entries are present in `literature/citations.bib` (verified):

1. McEnteggart 2015 (J Vasc Interv Radiol), `@mcenteggart2015readability`
2. Piersson 2025 (Eur Heart J Imaging Methods Pract), `@piersson2025readability`
3. Behers 2024 (Cureus), `@behers2024readability`
4. AHRQ PEMAT, `@ahrq_pemat`

The remaining citations in this document should be added to `citations.bib` after author-level verification.

## 7. Recommended next actions for the lit review

1. Run the targeted PubMed searches enumerated in §2.2 and §3.2 above. Add any closer prior comparators to §2.1 and §2.2.
2. Verify each "VERIFY" citation against PubMed; update the `citations.bib` file.
3. Pull two or three of the highest-impact AI-in-medicine citations (Singhal, Ayers, Lee, Pan, Goodman) at full text to confirm methodological framing.
4. Ask the clinical lead (Naeem) for the cardiology-imaging citations he would expect a reviewer at his journal of choice to want to see referenced.
