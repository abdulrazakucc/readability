# Literature

Background reading for the cardiac CT readability project. Read all four before touching Phase 1 of the pipeline.

## Files in this directory

| File                                                | What it is                                                                                  | Status     |
|-----------------------------------------------------|---------------------------------------------------------------------------------------------|------------|
| `piersson_2025_cmri_readability.pdf`                | Piersson et al. 2025, Eur Heart J Imaging Methods Pract — cardiac MRI patient-page readability | Full PDF   |
| `behers_2024_ai_chatbot_cardiac_cath_readability.pdf` | Behers et al. 2024, Cureus — readability of AI chatbot answers about cardiac catheterization | Full PDF   |
| `mcenteggart_2015_abstract.txt`                     | McEnteggart, Naeem et al. 2015, J Vasc Interv Radiol — IR readability (paywalled, abstract only) | Abstract   |
| `pemat_user_guide.pdf`                              | AHRQ PEMAT instrument and user guide                                                        | Full PDF   |
| `citations.bib`                                     | BibTeX entries for all four sources                                                         | BibTeX     |

## Why each one matters

### Piersson et al. 2025 — Cardiac MRI readability
The closest existing paper. Same six readability formulas, same patient-facing sites (BHF, RadiologyInfo, Mayo, Cleveland, AHA), but on cardiac MRI, not cardiac CT. **Read it to see exactly what to NOT repeat** — our novelty is (a) pre-procedure cardiac CT and (b) the AI rewrite arm.

### Behers et al. 2024 — AI chatbot readability for cardiac cath
Demonstrates the readability-of-AI-output methodology our Aim 2 builds on. They scored ChatGPT, Gemini, Copilot for cardiac catheterization PEMs. Our extension: we don't just score chatbot output, we ask chatbots to *rewrite existing patient pages* and we measure the accuracy/completeness trade-off (their study did not).

### McEnteggart, Naeem et al. 2015 — IR readability
The original readability methodology Naeem co-authored. Sets up the six-formula approach and the comparison-across-websites design we are extending. Paywalled at Elsevier; abstract is preserved here. If you have institutional access, drop the PDF in this directory and the manuscript citation will still work.

### PEMAT user guide (AHRQ)
Tool for scoring *understandability* and *actionability*, complementary to readability. The plan flags this as a possible secondary measure. Decision: defer for now; revisit if reviewers ask.

## Manual additions

If you find additional background as you read, drop the PDF here and add a row to the table above. Then add a BibTeX entry to `citations.bib`.

If you have access to the full JVIR McEnteggart 2015 PDF via Brown / Lifespan / institutional login, save it as `mcenteggart_2015_ir_readability.pdf`.
