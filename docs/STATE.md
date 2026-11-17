# Project state (2026-11-15)

Nothing is running. The corpus was re-chunked on 2026-11-15 (chunker fix, "c2"): 319,377 article passages instead of 230,545; everything below refers to c2 unless marked v1.

## Embeddings (all finished, nothing running)

| Model | Scope | Docs | Evaluated |
|---|---|---|---|
| multilingual-e5-small | articles | 319,377 | yes |
| multilingual-e5-base | articles | 319,377 | yes |
| bge-m3 | articles | 319,377 | yes |
| multilingual-e5-small | all prose | 1,728,678 | yes |

Vectors of texts that existed before the fix were copied from `data/index_v1/` (checked: re-encoding 150 reused and 150 new texts gives cosine >= 0.9995); only 66,538 new article texts were encoded. Backups of the earlier state: `data/index_v1/`, `data/processed/v1/` (chunks, index_docs, legal.db, article cache), `data/app/v1_backup/`, `data/app/v1_supplement/`.

`bge-m3` over all passages was not run (about 9 hours on the RTX 3050). To resume or rebuild every shard set:
`bash src/resume_embeddings.sh`; shards are atomic and `meta.json` guards against a changed
`index_docs.parquet`, which must not be rebuilt while shard folders exist.

## Other results already on disk

* BM25/TF-IDF/overlap, three analyzers, article scope and full corpus: `outputs/sparse_results_*.json`
* e5-small and e5-base dense/hybrid, English strategies: `outputs/dense_results_*.json`
* Title layer: `outputs/title_results.json`
* Report: `docs/results_retrieval.md`

## Repository hygiene (2026-11-06)

`README.md` (install, data, pipeline order with timings, app, tests, structure, limits), `requirements.txt` (pinned, PyTorch CUDA 13 from the
PyTorch index), `requirements-report.txt`, `.gitignore` (data/, logs/, caches). `src/00_download_data.py` downloads, checks (SHA-256) and unpacks
the raw data; checked on the existing files and on a small 7z archive, the `unrar` branch and the real download path were not run. Work logs
moved to `logs/`. The folder is still NOT a git repository.

## Report and presentation (2026-11-05)

`report/Отчёт_Поиск_по_законодательству_РК.docx` (+ PDF, 16 pages) and `report/Презентация_Поиск_по_законодательству_РК.pptx` (+ PDF, 15 slides,
speaker notes with likely questions), in Russian. Built by `report/build_report.py`, `report/build_slides.py` and `report/make_figures.py` from
`outputs/*.json` (judgments v1), so rebuilding after new results updates every number. Placeholders to fill: author, teacher, repository link
(title page and slide 1). References were written from memory except [1] and [2]; check their details before submitting.

## Report and slides refreshed (2026-11-09)

Screenshots now show the new light UI (`report/capture_screens.py`: headless Edge over the DevTools protocol, uses `?q=...&mode=...` URL parameters of the app);
report has 3 app figures and 17 pages, slide 13 has three screenshots. Text mentions the right-hand panel, the 53 example questions, article lookup, the
88,119-article supplement and that metrics predate it.

## Superseded: supplement layer (2026-11-08 to 2026-11-15)

The supplement of 88,119 articles (`36_build_extra_articles.py`, `37_embed_extra.py`) was removed on 2026-11-15 because the re-run of the pipeline made it part of the main index. The text below is history.

## Demo app changes of 2026-11-08

* Chunker accepts headings without a period ("Статья 1", "1-бап"): the Constitution and ~2,700 files per language (mostly treaties) had no articles.
  The research indexes and all reported metrics predate this fix; the app gets the missed articles as a supplement
  (`src/36_build_extra_articles.py` -> `data/app/extra_articles.parquet`, `src/37_embed_extra.py` -> `data/app/extra_emb/`, 88,119 passages, BM25 rebuilt
  by `33`). A full re-run of the pipeline would change chunk ids and require re-embedding everything.
* Exact reference lookup ("статья 1 Конституции РК"): `parse_reference` + `SearchEngine.lookup_reference` in `app/engine.py`.
* UI: settings panel on the right, all 53 test questions per language in the examples block, light palette, no framework.

## Demo app

`app/server.py` + `app/static/index.html` (engine in `app/engine.py`, guide in `app/README.md`). Run: `python app/server.py`. Streamlit was removed completely on 2026-11-09 (code, config, requirement, venv package); the page is plain HTML on the standard-library HTTP server.
Data for it is in `data/app/` (articles.parquet, acts.parquet, titles.parquet, bm25_*.npz, title_emb/) built by `src/33_build_app_data.py`
and `src/34_embed_titles.py`; article embeddings come from `data/index/emb_bge-m3_articles/`. A preview entry `legal-search`
(port 8610) was added to the shared `E:/project/.claude/launch.json`. Thumbs up/down are appended to `data/app/feedback.jsonl`.
Checked in the browser: article search in ru, kk and en, method comparison, act search by title. Not checked: filters other than the
defaults, CPU-only mode, the thumbs buttons.

## Judgments

`annotation/qrels_v1.json` = round 1 (hand-checked) + round 2 (pooled from eight system runs, 270 candidates read): 376 articles judged, 67 answer a need, 100 related, 209 rejected. Built by `30_pool_candidates.py` -> `32_merge_round2.py`; evaluation picks the version with `QRELS_VERSION=v1` (result files end in `_v1.json`; v0 files are kept for comparison). `annotation/review.html` now shows round 2 too.

## Behaviour changes of Stage 3 (2026-11-15)

`engine.search` now (a) reads an all-Latin query as Russian when that gives a higher top-1 score, (b) sets `low_confidence` and adds a warning when the best score is below `CONFIDENCE_MIN` (ru 0.62, kk 0.61, en 0.58), (c) adds the policy note for questions about evading the law (`docs/policy.md`). The server returns `low_confidence`; the page shows it as a warning line.

## 2026-11-17: English deliverables, part-corpus run, unified comparison, memory

* `report/Report_Kazakh_Legal_Search_Engine.pdf` (18 pages) and `report/Presentation_Kazakh_Legal_Search_Engine.pdf` (21 slides), English, built by `report/build_report_en.py` and `report/build_slides_en.py`.
* bge-m3 on a part of the corpus: `src/24_embed.py BAAI/bge-m3 part ...` (articles + 15% of other passages = 530,772 passages, 69 min), evaluated by `src/52_part_corpus_eval.py` -> `outputs/part_corpus_eval.json` (ru S@10 0.80, kk 0.69, en 0.67). The full-corpus run (D6) is still not done.
* `src/55_unified_comparison.py` -> `docs/results_unified.md` (Recall@1/5/10/20/50, MRR, nDCG for every method), `src/53_memory_benchmark.py` -> `outputs/memory_benchmark.json`.
* MIT `LICENSE` and `CREDITS.md`; team contributions and the three-language statement are in README and report. Interface text is still Russian (localisation to ru/kk/en planned).

## Stage 5 artefacts (2026-11-15)

`release/testset/`, `release/parallel/` (parquet is git-ignored; rebuild with `src/48_parallel_corpus.py`), `release/glossary/`, each with a datasheet and checksums; none published. Encoder sweep: `outputs/encoder_sweep.json` (models cached in the Hugging Face cache: bge-reranker-v2-m3, Qwen3-Embedding-0.6B, multilingual-e5-large).

## Cited LLM answer (2026-11-15)

Button "Ответ с цитатами" -> `/api/answer` -> `app/answer.py` + `app/llm.py` (Ollama `gemma3:4b` by default; `LLM_BACKEND`, `LLM_MODEL`, `ANTHROPIC_API_KEY`). Needs Ollama running (installed here). The Anthropic backend has never been run.

## Stage 4 additions (2026-11-15)

`app/amendments.py` (history and pending changes from footnotes), modes "Сравнить акты" (`group_by_act`), `/api/explain` (key sentences) and the quote summary button; `engine._hit` no longer slices the whole frame (search ~0.2 s). No LLM: A1 is extractive only.

## Page and engine additions (2026-11-15, second half of Stage 3)

Default mode is now "Автоматически" (`engine.route`). `engine.expand_abbreviations` runs before encoding and BM25. `/api/translate` (NLLB, loaded on first use, about 1.2 GB GPU) and `/api/config` (МРП from `app/mrp.json`) are new; the page marks deadlines and amounts. МРП must be updated by hand every year.

## Ranking (2026-11-15)

App defaults unchanged (filters on). New experimental switch "Приоритет кодексов и законов" (`Filters.force_prior`, 0.02 when ticked) is off by default. The re-ranker model `BAAI/bge-reranker-v2-m3` is in the Hugging Face cache but is not used by the app. Results: `outputs/rank_experiments.json`.

## Repository and tests

Git repository in this folder (branch `main`, 8 local commits by stage, not pushed). `python -m pytest tests -q` runs 23 tests; `RUN_GOLDEN=1` adds 23 golden queries that need the real indexes and GPU. CI: `.github/workflows/tests.yml`.

## Waiting on the author

* Licence, author, teacher and repository link for the report and slide 1 (roadmap C2); instructor approval of the extension (C3).

* Review of the query set in `annotation/review.html` (53 needs, 102 judgments, Kazakh queries need a native speaker).
* After that: a second round of judgments pooled from the systems' top results, because the first set is incomplete.

## Rebuild order if the data folder is lost

`01_csv_to_parquet` -> `05_link_texts` -> `08_build_db` -> `12_build_chunks` -> `14_load_passages` ->
`21_build_index_docs` -> `24_embed` (per model and scope). Raw archives are in `data/archives/`.
