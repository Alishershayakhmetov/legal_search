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

**Gate:** baseline table (v2) in `docs/results_retrieval.md` with intervals; the held-out set exists.

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

**Gate:** one chosen configuration; a before/after table for the report; latency per query measured.

## Stage 3: honest behaviour and usability (2 days)

| Item | Why now |
|---|---|
| S13 "no reliable answer" signal | needs the Stage 2 scores to calibrate |
| S14 query router; S11 robustness test set (typos, Latin letters, mixed languages) | measures failure modes; fix the cheap ones |
| U12 filter by branch of law; S30 year and place in the query | metadata already exists |
| A16 translate the snippet into the language of the question | English users now see Russian or Kazakh text |
| A4 monthly calculation index to tenge; A5 highlight deadlines and amounts | practical value, 3 h each |
| X8 policy for harmful or out-of-scope questions | short written policy plus a test |

**Gate:** robustness set results in the report; golden queries still pass; every new control checked in the browser.

## Stage 4: answers and depth (3–4 days)

| Item | Note |
|---|---|
| A10 amendment timeline from footnotes; A11 warning about changes not yet in force | data is already in the passages |
| A13 table for one question across regimes (Labour Code, civil service, police service) | turns a known error type into a feature |
| S19 explain a result (highlight the closest sentences) | also helps error analysis |
| **LLM** A1 short answer with citations and a check that every citation exists in the retrieved text | only if the LLM question is settled; always labelled "not legal advice" |

**Gate:** each feature has a test and an entry in the user guide; for A1 a rate of unsupported citations measured on the test set.

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
