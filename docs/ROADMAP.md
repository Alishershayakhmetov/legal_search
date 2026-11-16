# Roadmap: features by stage

Ids refer to [IDEAS.md](IDEAS.md). Estimates are working days of one person plus unattended GPU time. Rules for every stage:

1. **Measure before and after.** Any ranking change is evaluated on the test set (`QRELS_VERSION=v1`, later the held-out part) and the result is saved in `outputs/` and added to the report as a before/after row.
2. **One change per commit**, so a bad idea can be reverted.
3. **Golden queries (E12) run in the tests** from Stage 0 on; a failing golden query blocks a change until it is explained.
4. A stage ends with its **gate**; do not start the next stage before the gate is met.

Decision needed before Stage 4: is an LLM available (API key or local model)? Items marked **LLM** (A1, A14, A15, S5, S27, S28, E10) wait for that answer.

## Stage 0: hygiene (0.5 day)

| Item | Result |
|---|---|
| C1 git repository, commits by stage (the author pushes) | history for the "reproducibility" criterion |
| C2 licence, author, teacher and repository link in the report and slide 1; C4 check references | no placeholders left |
| U9 small fixes (Constitution kind, amending acts titled «Закон … о внесении изменений») | polish |
| X5 do not store raw queries in `feedback.jsonl` without consent | privacy |
| X1 CI (tests on every push); E12 golden queries (20) | safety net for the next stages |

**Status 2026-11-15: done except C2.**
* C1: local repository with 8 commits by stage; nothing pushed, no GitHub repository created.
* C4: all references found by web search; [12] (Sparck Jones & van Rijsbergen, BL R&D Report 5266) is dated 1975 or 1976 depending on the source.
* U9, X5, X1, E12 done: `tidy_metadata` in `app/engine.py`; feedback stores a query hash unless the consent box is ticked; `.github/workflows/tests.yml` (clean Python 3.12 venv, no torch: 23 passed, 23 skipped); `annotation/golden_queries.json` with 23 cases (`RUN_GOLDEN=1 python -m pytest tests/test_golden.py`: 23 passed in about 42 s with the real engine).
* C2 waits for the author: licence, author, teacher and repository fields in the report and on slide 1.

**Gate:** tests and golden queries pass on a clean clone.

## Stage 1: trust in the numbers (1–2 days, mostly waiting)

| Item | Result |
|---|---|
| D5 re-run the pipeline with the fixed chunker, re-embed, re-evaluate (background GPU, several hours) | a new baseline "v2" with the missing 88 thousand articles |
| E1 author reviews `annotation/review.html`; kazakh queries by a native speaker (author's time, in parallel) | judgments v2 |
| E5 paired bootstrap tests; E6 metrics by query type and branch of law | claims with significance |
| E3 start writing 100–150 more questions by other people, keep a held-out part | tuning data that does not overfit |

**Status 2026-11-15:** D5, E5, E6 done; E1 and E3 wait for people.
* D5: chunker fix applied end to end (`12` -> `14` -> `21` -> `24` with vector reuse -> `22`/`25`/`35`), baseline "c2" in `outputs/*_v1_c2.json` and `docs/results_retrieval.md`; the earlier runs are kept as `*_v1_c1.json`. Result: Success@10 unchanged for bge-m3 (ru 0.80, kk 0.73), MRR@10 lower by 0.00-0.05 (more competing articles); e5-small ru 0.58 -> 0.53; BM25 and the ranking of systems unchanged. Paired counts bge-m3/BM25 identical to before. The app supplement is gone; 23 unit tests and 23 golden queries pass on the new index.
* E5/E6: `src/39_significance.py` -> `outputs/significance.json` and a table plus text in section 5.2 of the report. bge-m3 beats BM25 (ru p=0.0002, kk p<0.001) and, on Kazakh, both e5 models; on Russian bge-m3 vs e5-base is not significant (p=0.18); equal-weight hybrid is significantly worse than bge-m3; the three English strategies are not distinguishable. Weak spots: procedure (ru 0.33), civil law in Kazakh (0.25) - groups of 1-7 needs.
* Not done: E1 (author review), E3 (questions from other people, held-out split). **The gate is not met until the held-out set exists.**

## Stage 2: ranking improvements (2–3 days)

Run in this order, each measured against the baseline; keep only what helps on the held-out part.

| Order | Item | Note |
|---|---|---|
| 1 | S26 query instructions | 3 h, no re-encoding |
| 2 | S22 legal-force prior and S3 penalty for bills, old editions and special regimes | 3 h each |
| 3 | S12 abbreviation and synonym dictionary | 3 h |
| 4 | **S2 re-ranker (bge-reranker-v2-m3) on the top 30** | 0.5 day; check latency |
| 5 | S6 hybrid weights tuned on the held-out part | 2 h |
| 6 | S23 and S24 ablations (passage size, input length) | GPU in the background; these may change every number, so report them even if they do not help |

**Status 2026-11-15 (no held-out set exists, so every variant had fixed settings and is reported with a paired test):** `src/40_rank_experiments.py` -> `outputs/rank_experiments.json`, report section 5.9, one new slide.
* S26 instructions: hurt bge-m3 on all languages (ru S@10 0.80 -> 0.62-0.71, kk 0.73 -> 0.53-0.62). Dropped.
* S3: the demo's default filters (no repealed acts, drafts, amending acts) are the biggest gain: ru MRR@10 0.383 -> 0.680, S@1 0.18 -> 0.56; kk 0.354 -> 0.565; en 0.321 -> 0.519. Already on in the app; the unfiltered numbers of Stage 1 understate what the user sees.
* S22 legal-force prior (Constitution > constitutional law > code > law > decree), +0.02 on the cosine score, on top of filters: ru S@1 0.69, MRR 0.765; kk MRR 0.660; en 0.671; weight 0.1 is too much (ru MRR 0.599). Gold articles are 52 of 67 codes, so the test set favours this prior; **added to the app as an off-by-default switch** ("experimental") until the held-out set confirms it.
* S2 re-ranker bge-reranker-v2-m3 on the top 30 (act title + text): +about 650 ms per query; alone raises MRR (ru 0.383 -> 0.512) but on top of filters it does not help (ru MRR 0.680 -> 0.666). **Not added.**
* S12 dictionary: cannot be measured (one test question has an abbreviation); moved to the Stage 3 robustness set. S6, S23, S24 not run (S6 needs the held-out set, S23/S24 need re-chunking and re-embedding).
* **Gate not met:** the chosen configuration (filters on, prior off) is the current default; the prior waits for E3.

## Stage 3: honest behaviour and usability (2 days)

| Item | Why now |
|---|---|
| S13 "no reliable answer" signal | needs the Stage 2 scores to calibrate |
| S14 query router; S11 robustness test set (typos, Latin letters, mixed languages) | measures failure modes; fix the cheap ones |
| U12 filter by branch of law; S30 year and place in the query | metadata already exists |
| A16 translate the snippet into the language of the question | English users now see Russian or Kazakh text |
| A4 monthly calculation index to tenge; A5 highlight deadlines and amounts | practical value, 3 h each |
| X8 policy for harmful or out-of-scope questions | short written policy plus a test |

**Status 2026-11-15:** done S11, S13, X8, S14, S12, A16, A4, A5 (+ the transliteration fix); not done U12 (blocked) and S30 (not implemented, see below).
* S11: `src/41_robustness.py` makes 6 perturbed versions of the 45 needs per language (typos light/heavy, Latin letters, no punctuation, 4 keywords, ru+kk mixed) -> `annotation/robustness_queries.jsonl`, `outputs/robustness.json`, report 5.10, slide 14. Typos and missing punctuation cost little (ru S@10 0.93 -> 0.87-0.96); 4 keywords 0.73; Latin-letter Russian 0.58 -> 0.93 with the new back-transliteration (engine reads an all-Latin query both ways and keeps the more confident reading); Latin-letter Kazakh 0.02 -> 0.47 only; ru+kk mixed 0.87.
* S13: top-1 cosine separates 45 in-scope from 20 off-topic questions per language with AUC 1.0 (margin to the 10th: 0.57, useless); thresholds ru 0.62 / kk 0.61 / en 0.58 (5% quantile of in-scope) flag all 20 off-topic and 6 borderline questions per language. The page shows a warning and still shows results. Threshold fitted on the same 45 questions per language: false-flag rate on new questions unconfirmed.
* X8: `docs/policy.md`, `engine.policy_notice` (evasion questions get a reminder; liability questions do not), 3 unit tests plus 3 behaviour tests (`RUN_GOLDEN=1`). Checked in the browser (Latin query, off-topic query, evasion query; warning style).
* S12: `engine.expand_abbreviations` (about 25 upper-case abbreviations spelled out before encoding); `src/42_abbreviations.py` on 14 hand-written questions: the expected act is in the top 5 with and without it (14/14, ceiling), first result 7/14 -> 12/14 (5 better, 0 worse; descriptive, my own questions).
* S14: mode "Автоматически" (default) = `engine.route_query`: no article number, at most 7 words and top act-title similarity >= top article similarity -> act search; `src/43_router_eval.py`: 159/159 correct on the test set's 24 title queries and 135 questions (AUC of the score difference 0.998); the class gap is thin (-0.013 vs +0.018) and was read from the same queries, so unconfirmed.
* A5: yellow deadlines and green amounts/percentages/penalties in snippet and full text (regex in the page; Unicode-aware, a first version with `\w` missed Cyrillic and was caught in the browser). A4: МРП -> tenge using `app/mrp.json` (4 325 tenge for 2026, dated, with source link; checked against news reports on 2026-11-15, not against the law text itself; **update every year**). A16: "Translate to English" button for English queries (NLLB-200 600M on demand, labelled unofficial, only the beginning of long text).
* U12 not done: the 351 legal-area codes in the metadata have no names (only classifier codes like 005022002000). S30 not implemented: region names go down to rural districts and "в 2015 году" does not mean "adopted in 2015" (editions by date are not in the data).
* Gate: robustness results are in the report; the 23 golden queries pass (28 behaviour/golden tests in total); highlighting, МРП conversion, router, translation, warning and Latin reading were checked through the browser pane.

## Stage 4: answers and depth (3–4 days)

| Item | Note |
|---|---|
| A10 amendment timeline from footnotes; A11 warning about changes not yet in force | data is already in the passages |
| A13 table for one question across regimes (Labour Code, civil service, police service) | turns a known error type into a feature |
| S19 explain a result (highlight the closest sentences) | also helps error analysis |
| **LLM** A1 short answer with citations and a check that every citation exists in the retrieved text | only if the LLM question is settled; always labelled "not legal advice" |

**Status 2026-11-15:** A10, A11, A13, S19 done; A1 done only in an extractive form (no LLM).
* A10/A11: `app/amendments.py` reads footnotes ("Сноска."/"Ескерту.") into a history (action, date, number, entry into force) and "Примечание ИЗПИ!"/"ЗҚАИ-ның ескертпесі!" notes into warnings with a status against today and the 01.04.2024 snapshot. Coverage (`src/44_amendments_check.py`): footnotes in 13,363 ru / 13,306 kk articles, parsed 99.5% / 99.2%, 60,406 entries, 12,610 with an exact date; 34 random parses read by hand (errors found and fixed: kk relative days, "бастап", duplicates, spelled-out dates, empty ИЗПИ markers). 8 unit tests. Shown in the card as a collapsible history and warning lines.
* A13: mode "Сравнить акты (режимы)" = one best article per act (`engine.group_by_act`), `src/45_regimes_eval.py`: the gold act is among the 5 acts in 44/45 ru, 44/45 kk, 40/45 en, but the exact gold article among the best-per-act articles is found less often than in the plain top 5 (ru 33 vs 38), so it complements, not replaces, the list.
* S19: "Показать ключевые предложения" (`engine.explain`, sentence-level bge-m3 similarity, highlighted in the full text).
* A1 (extractive form): button "Краткая выжимка" = the best sentence of each of the top 3 articles as a verbatim quote with act and article; no invented citations possible by construction, selection quality not measured; hidden when the no-reliable-answer warning is on. The author chose a local model now and a key at the end.
* A1 LLM answer: `app/llm.py` (Ollama backend, default `gemma3:4b`, 25 tok/s, 10-20 s per answer; Anthropic backend written but never run - no key) and `app/answer.py` (4 excerpts of key sentences -> prompt -> per-sentence checks: existing citation, numbers present in the cited excerpt incl. spelled-out ru/kk numbers, bge-m3 support >= 0.65). `src/46_answer_eval.py` on 135 questions: answered 44/39/43 of 45 (ru/kk/en), gold article among the excerpts 37/31/32; per sentence without citation 10%/24%/11%, nonexistent citation 3%/1%/1%, number not in excerpt 4%/1%/1%; kept after all checks 81%/65%/71%. Manual read of 42 passing sentences (`outputs/answer_audit.json`, by me, not a lawyer): unsupported 0/14 ru, 2/12 kk, 3/16 en (5 of 42), unclear 3, about a fifth faithful but off-topic. The checks catch invented citations and numbers but not distortions inside one article. Found and fixed: English questions got Russian answers until the prompt asked for English explicitly (2 of 45 still contain Cyrillic). `qwen2.5:3b` was weaker in Kazakh in a probe. The key (Anthropic API) is the author's to provide; with LLM_BACKEND=anthropic only the text source changes.
* Side finding: building result cards cost 0.3 s per hit (full-frame `iloc` per twin); fixed, search now ~0.15-0.2 s instead of 1.7 s, golden suite 44 s instead of 180 s.
* Gate: each feature has unit tests (38 passed, 28 behaviour/golden) and was checked in the browser pane; the user guide (`app/README.md`) was not extended. The unsupported-citation rate for A1 is 0 by construction for the extractive form and not applicable otherwise.

## Stage 5: contributions beyond the course minimum (optional, 3–5 days)

| Item | Result |
|---|---|
| D8 parallel Russian–Kazakh corpus with an alignment check; D10 term glossary from it | a dataset and a by-product with value of its own |
| D9 publish the test set with a datasheet; D12 personal-data scan first | benchmark; supports the extension bonus |
| S25 model sweep (larger and newer encoders) | may replace bge-m3 |
| D6 bge-m3 over all passages (about 9 h of GPU) | closes a stated limitation |

**Gate:** each published artefact has a licence and a datasheet; the instructor has approved the extension.

## Stage 6: report, slides, defense (1–2 days)

- Rebuild the report and slides from the new `outputs/` (`report/build_*.py`); add the before/after tables, the robustness results and the limits that remain.
- E13 small user study (5–10 people, SUS) and E14 manual comparison with the official site search on 20 questions, if time allows.
- Rehearse the defense with the speaker notes; update README, `docs/STATE.md` and the screenshots.

## If time is short

Minimum useful path (3–4 days): Stage 0, then from Stage 1 only D5 and E5, then S3 + S2, then S13 and A16, then Stage 6. Everything else stays in the backlog.

## Rough schedule

| Stage | Working days | Can overlap with |
|---|---|---|
| 0 | 0.5 | — |
| 1 | 1–2 | Stage 2 once the baseline exists; the author's review runs alongside everything |
| 2 | 2–3 | Stage 3 UI work |
| 3 | 2 | Stage 2 GPU runs |
| 4 | 3–4 | — |
| 5 | 3–5 (optional) | Stage 4 |
| 6 | 1–2 | — |
| Total | about 10–15 | |
