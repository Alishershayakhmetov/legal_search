# Ideas backlog

Status: `idea` (not started), `next` (planned), `done`. Effort is a rough estimate. Add new ideas at the end of the matching section and
keep the "Log" at the bottom up to date. Every search idea should be measured before/after on the test set (`QRELS_VERSION=v1`).

## Search quality

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| S1 | Put the act title into the text that is embedded ("Трудовой кодекс, ст. 113: …") | The encoder does not see which act an article belongs to | re-embed, 1–1.5 h | idea |
| S2 | Re-rank the top 30 with bge-reranker-v2-m3 | Removes near-miss articles; usually the biggest gain | 0.5 day, +0.3–1 s per query | done 2026-11-15: no gain on top of filters, +650 ms, not added |
| S3 | Penalty for bills, old editions and special regimes; bonus for codes | Fixes errors from the error analysis (police-service law above the Labour Code) | 2–3 h | done 2026-11-15 as the default filters (big gain) |
| S4 | Detect the user's category ("я госслужащий", "ИП", "пенсионер") and filter by it | General vs special regulation | 1 day | idea |
| S5 | LLM query rewriting (everyday words → legal terms) | Bridges the vocabulary gap | 0.5 day, needs an LLM | idea |
| S6 | Hybrid with weights tuned on a held-out part of the questions | Equal-weight RRF hurt; BM25 may still help on names and numbers | 2 h, needs more questions | idea |
| S7 | Related articles ("см. статью N", neighbours in the same code) | The answer is often in 2–3 linked articles | 1 day | idea |
| S8 | Cross-reference graph between acts + PageRank as a ranking signal | "What cites this article"; authority prior | 1–2 days | idea |
| S9 | Passage-level answer extraction (highlight the sentence that answers) | Faster reading, easier to judge | 1 day | idea |
| S10 | Fine-tune a small encoder on pairs from 👍/👎 feedback and pooled judgments | Domain adaptation; needs a few thousand pairs | 2–3 days | idea |

## Answers, not only a list

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| A1 | Short answer written only from the retrieved articles, with citations ("ТК, ст. 113") and a check that every cited sentence exists | Most visible demo feature; the check guards against invented citations | 2 days, needs an LLM | done 2026-11-15 with a local model (gemma3:4b) and per-sentence checks; key later |
| A2 | Clarifying question when the query is ambiguous | Fewer wrong-regime answers | 1 day | idea |
| A3 | Compare editions of an article over time | History file is missing from the repository, needs another source | 2+ days | idea |

## Data and coverage

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| D1 | Items and sub-items of acts without articles (orders, resolutions) as passages | They are outside the main index now | 1 day | idea |
| D2 | English titles for acts (NLLB) and an English title index | Closes strategy C from the report | 0.5 day | idea |
| D3 | Court practice (normative resolutions of the Supreme Court) as another layer | Interpretation next to the law | 2+ days | idea |
| D4 | Script that detects new versions of the source data and rebuilds only what changed | Laws change | 1–2 days | idea |
| D5 | Re-run the whole pipeline with the fixed chunker and recompute every metric | Metrics currently predate the fix (88 119 articles missing) | several hours of GPU | done 2026-11-15 (about 1 h with vector reuse) |
| D6 | bge-m3 over all 1.7 M passages | Best model was only tested on articles (about 9 h) | 9 h GPU | not run: ~7 GPU hours left |

## Evaluation and reliability

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| E1 | Independent review of the judgments in `annotation/review.html`, Kazakh queries by a native speaker | All numbers are provisional until then | author's time | next |
| E2 | Second annotator and Cohen's kappa | Shows the judgments are reliable | 1 day | idea |
| E3 | 100–150 questions per language, written by other people, plus a held-out part | 45 per language gives intervals of about ±0.1 | 2–3 days | idea |
| E4 | Turn `data/app/feedback.jsonl` into extra judgments automatically | Free relevance data from use | 2 h | idea |
| E5 | Paired bootstrap significance test between methods | Stronger claims in the report | 2 h | done 2026-11-15 |
| E6 | Metrics by query type (situation / concept / title) and by branch of law | Shows where the system is weak | 2 h | done 2026-11-15 (groups are tiny) |

## App and usability

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| U1 | Kazakh and English interface; highlight matched words | Audience and readability | 0.5 day | idea |
| U2 | Export found articles to Word/PDF with citations and links; "copy citation" | Practical use | 0.5 day | idea |
| U3 | Query history, shareable links (the `?q=` link already works) | Convenience | 2 h | idea |
| U4 | Voice input (browser speech recognition) | Accessibility, demo effect | 2 h | idea |
| U5 | Console menu as a fallback for the defense and for CI | The course accepts either UI | 2 h | idea |
| U6 | Docker image or a one-script installer | Runs on another computer without manual steps | 0.5 day | idea |
| U7 | Telegram bot on top of the same engine | Reach; reuse of bot experience | 1 day | idea |
| U8 | Show the article number prominently, deep link to the article text | Link now opens the whole act | 1 day, site renders by JavaScript | idea |
| U9 | Fix small things: Constitution shown as kind "Другое"; amending acts titled «Закон … о внесении изменений» are not hidden | Polish | 1 h | done 2026-11-15 |

## Course deliverables

| # | Idea | Status |
|---|---|---|
| C1 | `git init`, commits by stage, push to GitHub (by the author) | local commits done 2026-11-15; push is up to the author |
| C2 | Choose a code licence; fill author, teacher and repository link in the report and slide 1 | next |
| C3 | Agree the extension with the instructor (bonus up to 5 points) | next |
| C4 | Verify the references typed from memory ([3]–[12]) | done 2026-11-15 (all found; [12] year 1975/1976 varies by source) |
| C5 | Bigger screenshots on the demo slide; rehearse the answers in the speaker notes | idea |

## Third batch (2026-11-15)

### Search quality and robustness

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| S11 | Robustness test set: typos, Latin-letter Kazakh/Russian ("kak vzyskat alimenty"), Kazakh-Russian code-switching, very short queries | Real users do not type like the test set; measures failure modes | 0.5 day | done 2026-11-15 |
| S12 | Dictionary of abbreviations and synonyms (ТК, ГК, КоАП, МРП, БИН, ИП, ТОО) used for query expansion | Cheap, deterministic; part of it exists for article references only | 3 h | done 2026-11-15 (top-1 7/14 -> 12/14 on 14 own questions) |
| S13 | "No reliable answer" signal: abstain when the score of the best result and its margin over the 10th are low; calibrate the threshold | Honest behaviour for out-of-scope questions ("как приготовить плов") | 3 h | done 2026-11-15 |
| S14 | Query router: classify a query as article reference / act title / situation and pick the layer automatically | Removes the need to switch modes by hand | 0.5 day | done 2026-11-15 (mode "Автоматически") |
| S15 | Better Kazakh morphology for BM25 (proper analyzer instead of the home-made suffix stripper) | The stripper did not beat five letters; a real analyzer might | 1 day | idea |
| S16 | Hard negatives from the error analysis and 👎 clicks for re-ranker or encoder training | Directly targets the four error types | 1 day | idea |
| S17 | Show the same norm repeated in several laws as one result with "also in: …" | Fewer duplicates in the list | 0.5 day | idea |

### Practical answers

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| A4 | Convert fines and thresholds given in monthly calculation indices (МРП) to tenge using the current МРП value | "Штраф 10 МРП" means nothing to most readers; value must be entered and dated | 3 h | done 2026-11-15 (app/mrp.json, update yearly) |
| A5 | Extract and highlight deadlines, amounts, percentages and penalties in a result ("не позднее 10 дней", "до 80 МРП") | Quick scan of what matters | 0.5 day | done 2026-11-15 (highlight in the page) |
| A6 | Penalty table for administrative and criminal articles (fine, arrest, imprisonment) in a fixed format | Makes "what is the punishment" answerable at a glance | 1 day | idea |
| A7 | "Ситуация → пошаговый чек-лист" template for common cases (dismissal, divorce, loan) built from linked articles | High user value; needs legal review | 2+ days | idea |

### Data and evaluation

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| D7 | Synthetic questions generated from articles by an LLM, used for training and for a larger (silver) test set | Scale without hand annotation; keep separate from the gold set | 1–2 days | idea |
| E7 | Active-learning review order in `review.html`: show the judgments the systems disagree on first | The author's review time goes where it matters | 3 h | idea |
| E8 | Data card and model card (sources, licences, known gaps, intended use) + `CITATION.cff` | Expected for a public dataset project | 2 h | idea |
| E9 | Manifest of data hashes (like `meta.json` for embeddings) for every stage | Detects silent mismatches between stages | 3 h | idea |

### Engineering and app

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| X1 | GitHub Actions: run the tests and a lint on every push | Part of "code quality"; cheap | 1 h | done 2026-11-15 (tests only, no lint) |
| X2 | CPU-only mode: ONNX/int8 encoder and an approximate index (HNSW) | Runs on a laptop without a GPU; latency measurement for the report | 1 day | idea |
| X3 | Smaller index: truncate embeddings to 256–512 dimensions or int8 and measure the quality loss | Memory and disk cost table for the report | 0.5 day | idea |
| X4 | Cache query embeddings and results of repeated queries | Faster repeats, simpler load test | 1 h | done 2026-11-15 |
| X5 | Privacy: do not store query text in `feedback.jsonl` unless the user agrees; document what is stored | The file currently keeps raw queries | 1 h | done 2026-11-15 (hash by default, text only with the checkbox) |
| X6 | If the server is ever exposed beyond localhost: rate limit, request size limits (partly present), no directory listing | Basic safety | 2 h | idea |
| U10 | Accessibility: keyboard navigation, labels for screen readers, contrast check of the palette | Quality, low effort | 3 h | idea |
| U11 | Usage statistics page (questions per language, share of 👍/👎, slow queries) | Evidence for the report and for tuning | 0.5 day | idea |

## Fourth batch (2026-11-15)

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| S18 | Use bge-m3's own sparse (lexical-weight) and multi-vector outputs, fused with the dense score | The model offers all three scores; a hybrid inside one model may avoid the BM25 weakness seen in the equal-weight RRF | 1 day (re-encode, bigger index) | idea |
| S19 | Explain a result: highlight the sentences closest to the query and show the score per sentence | Trust and faster reading; helps error analysis | 1 day | done 2026-11-15 |
| S20 | Long-query mode: paste a contract clause or a paragraph of a letter and get the relevant articles | Real use case; needs chunking of the query | 0.5 day | idea |
| A8 | Term definitions: "что такое …" goes to the "Основные понятия" article of the act and shows the definition; hover on terms in results | Definitions are a frequent need; the articles already exist in the index | 1 day | idea |
| A9 | Deadline calculator: from a date and a rule found in the article ("в течение 10 рабочих дней") compute the last day with the calendar of holidays | Practical; needs the holiday calendar | 1 day | idea |
| D8 | Parallel Russian–Kazakh article corpus (68 111 acts have both texts): align by act and article number, check that the pair really matches (embedding similarity), release as a dataset | A by-product with value of its own; also tests cross-lingual retrieval (Kazakh query → Russian article) | 1–2 days | done 2026-11-15 (local, unpublished) |
| D9 | Publish the test set (needs, queries, judgments, guidelines) as a small dataset with a datasheet | Reusable benchmark; supports the extension bonus | 0.5 day | done 2026-11-15 (local, unpublished) |
| E10 | Second annotator: an LLM judges the same pairs; compare with the author and report agreement, never replace human review | Cheap check of the judgments; clearly labelled as a model | 0.5 day, needs an LLM | idea |
| U12 | Filter by branch of law (351 areas already in the metadata) | Cheap facet; narrows results the way lawyers think | 3 h | blocked 2026-11-15: area codes have no names in the data |
| U13 | Browse by topic: clusters of articles or the area tree with counts | Exploration when the user does not know what to ask | 1–2 days | idea |
| U14 | Phone-friendly layout and offline installable page (PWA) | The page is a plain HTML file, so this is cheap; the right panel already collapses under 960 px | 3 h | idea |

## Fifth batch (2026-11-15)

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| S21 | Autocomplete from the test questions and act titles; "did you mean" for typos using the corpus vocabulary | Fewer empty or poor searches | 0.5 day | idea |
| S22 | Prior from legal force (Constitution > codes > laws > by-laws; the `legal_force` field exists) | Higher-ranking norms first when texts compete | 3 h, measure on the test set | done 2026-11-15: helps on the test set, off by default until the held-out set |
| S23 | Ablation of passage size and overlap (1 500 / 800 chars, with and without overlap) | Never tested; may change every number | 1 day (re-chunk, re-embed) | idea |
| S24 | Ablation of the encoder input length (256 / 384 / 512 tokens) | 8% of passages are cut at 384; shows what that costs | 0.5 day | idea |
| A10 | Amendment timeline of an article from the footnotes in the text ("Сноска. … с изменениями, внесенными законами РК от …") | History without the missing history file; the data is already in the passages | 1–2 days | done 2026-11-15 |
| A11 | Warning about changes not yet in force from the "Примечание ИЗПИ! … вводится в действие …" notes | The user sees that the text will change | 0.5 day | done 2026-11-15 |
| A12 | "Куда обращаться": name the competent body from the article and the metadata (adopting and regulatory body) | Practical next step for the user | 1–2 days | idea |
| A13 | Compare one question across regimes in a table (Labour Code vs Law on civil service vs police service) | Turns the "general vs special regime" error into a feature | 1 day | done 2026-11-15 (act-grouped view) |
| D10 | Kazakh–Russian legal term glossary mined from the parallel article corpus (D8) | Useful to translators; by-product with value of its own | 1–2 days | done 2026-11-15 (local, unpublished) |
| D11 | Classifier of article role (definition, right, duty, liability, procedure, deadline) as a filter and a ranking hint | "What is the punishment" wants liability articles | 2 days | idea |
| E11 | Retrievability audit: which articles are never returned for any question (index health, hubness) | Finds dead zones of the index | 0.5 day | idea |
| E12 | Golden queries: 20 fixed questions with the expected top article, run in the tests/CI after every change | Catches regressions when the index or ranking changes | 3 h | done 2026-11-15 (23 cases, RUN_GOLDEN=1) |
| E13 | Small user study: 5–10 people, task completion and SUS usability score | Strong evidence for the defense | 1–2 days, needs people | idea |
| E14 | Manual comparison with the official site search on 20 questions (no scraping, by hand) | A real-world baseline for the report | 3 h | idea |
| U15 | Side-by-side Russian/Kazakh view of an article, aligned by paragraph | Helps verify translations and learn terms | 1 day | idea |
| X7 | Load test (concurrent requests, latency percentiles) of the server | Numbers for the report; finds locking problems | 3 h | idea |
| X8 | Policy for harmful or out-of-scope questions ("как обойти закон"): neutral answer, no advice on evasion | Responsible use; short written policy plus a test | 2 h | done 2026-11-15 |

## Sixth batch (2026-11-15)

| # | Idea | Why | Effort | Status |
|---|---|---|---|---|
| S25 | Model sweep on the article index: multilingual-e5-large, Qwen3-Embedding, jina-embeddings-v3, gte-multilingual, LaBSE | Only three models were compared; a bigger or newer one may beat bge-m3 on Kazakh | 0.5–1 day per large model (encoding hours) | done 2026-11-15 (local, unpublished) |
| S26 | Query instructions ("Represent this legal question for retrieving articles of Kazakh law") for models that support them | Free quality change, never tried | 3 h | done 2026-11-15: hurts bge-m3, dropped |
| S27 | Document expansion: generate the questions each article answers (doc2query) and embed them next to the article | Attacks the everyday-vs-legal vocabulary gap from the document side | 2 days, needs an LLM, big index growth | idea |
| S28 | HyDE: let an LLM write a short hypothetical answer, embed it instead of the question | Often helps vague situational questions | 0.5 day, needs an LLM | idea |
| S29 | Distil bge-m3 rankings into a small fast encoder (e5-small size) | Near bge-m3 quality on CPU | 3 days | idea |
| S30 | Year and place awareness in queries ("в 2015 году", "в Алматы") used as filters on year and region (both fields exist) | Local acts of akimats and maslikhats are 40% of the corpus | 1 day | not implemented: regions too fine, year semantics unclear |
| A14 | One-line plain-language summary above each result | Faster scanning; must be labelled as a summary, not the law | 1 day, needs an LLM | idea |
| A15 | "Объясни простыми словами" button with a disclaimer | Readability for non-lawyers; risk of distortion, show the original next to it | 1 day, needs an LLM | idea |
| A16 | Translate the shown snippet into the language of the question when only another language is available (English users now get Russian or Kazakh text) | Closes a visible gap of the English mode | 0.5 day (NLLB already installed) | done 2026-11-15 (on-demand button) |
| A17 | Read-aloud of an article (text to speech) | Accessibility | 0.5 day | idea |
| D12 | Personal-data scan of the texts before any release of the parallel corpus or the test set | Court-related texts may contain names; legal and ethical check | 0.5 day | done 2026-11-15 (local, unpublished) |
| E15 | Interleaving experiment to compare two rankings on live use of 👍/👎 | Online evaluation without new annotation | 1 day | idea |
| X9 | One command that runs the pipeline and skips stages whose inputs did not change (Makefile or small runner with hashes) | README now lists 11 manual steps | 1 day | idea |
| X10 | Developer guide: architecture diagram, data flow, how to add a ranking idea and measure it | Handover and defense | 0.5 day | idea |
| X11 | Installable package with a command line (`legalsearch search "…"`) | Reuse outside the web page | 1 day | idea |

Note: returns are diminishing. Most of the high-value items are in the earlier batches (S2, S13, A4, U12, E1, E12, C1); this batch is mostly
model and prompt experiments and polish.

## Log

- 2026-11-15: first batch (S1–S7, A1–A3, D1–D4, D6, E1–E3, U1–U8, C1–C4) proposed in chat.
- 2026-11-15: second batch added: S8–S10, D5, E4–E6, U9, C5 (found while reviewing the open problems of the report and the app).
- 2026-11-15: third batch added (S11–S17, A4–A7, D7, E7–E9, X1–X6, U10–U11). The user asked to implement re-ranking (S2) and then switched to finding ideas; S2 is not started.
- 2026-11-15: fourth batch added (S18–S20, A8–A9, D8–D9, E10, U12–U14).
- 2026-11-15: fifth batch added (S21–S24, A10–A13, D10–D11, E11–E14, U15, X7–X8).
- 2026-11-15: sixth batch added (S25–S30, A14–A17, D12, E15, X9–X11).
- 2026-11-15: staged plan written in docs/ROADMAP.md (stages 0-6, gates, minimum path).
