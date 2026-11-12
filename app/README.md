# Demo: search Kazakh legislation in Kazakh, Russian or English

A question in your own words returns the articles of codes and laws that answer it, with the article text in the
language of the question, the Kazakh and Russian versions side by side, and a link to the act on adilet.zan.kz.

## Run

```bash
cd /e/project/legal_search
.venv/Scripts/python app/server.py
```

The first start loads the indexes and the bge-m3 encoder (about a minute); later questions take 1-4 seconds.
It needs the files in `data/app/` and `data/index/emb_bge-m3_articles/`. To rebuild them:

```bash
cd src
../.venv/Scripts/python.exe -X utf8 36_build_extra_articles.py # articles whose headings have no period (Constitution, treaties)
../.venv/Scripts/python.exe -X utf8 37_embed_extra.py          # their embeddings (about 17 minutes)
../.venv/Scripts/python.exe -X utf8 33_build_app_data.py      # tables and BM25 indexes (needs data/index/emb_bge-m3_articles)
../.venv/Scripts/python.exe -X utf8 34_embed_titles.py        # title embeddings for the "find an act" mode (about 20 minutes)
```

A GPU (4 GB is enough) makes a question take about a second; without one the encoder runs on the CPU and takes several
seconds per question.

## What it does

The settings (mode, method, number of results, filters) are in a fixed panel on the right. "Примеры запросов" lists all 53 questions of the
test set for each language; a click puts the question into the search box. A query that names an article ("статья 1 Конституции РК",
"ст. 188 УК", "52-бап") also gets that article looked up exactly and shown first: the act is found by title, the article by number.
The page is plain HTML served by the Python standard library (`app/server.py`, `app/static/index.html`); no web framework is needed. Links can pre-fill it: `http://localhost:8610/?q=статья 1 конституции рк&mode=articles` (mode: articles, titles, compare).


| Mode | What you get |
|---|---|
| Search articles | bge-m3 semantic search (default), BM25, or a hybrid of both over 318,664 article passages (230,545 from the research index plus 88,119 supplementary ones) |
| Find an act by name | acts whose Russian or Kazakh title is closest in meaning to the query |
| Compare methods | the three methods side by side for the same question |

Filters: in-force acts only, hide bills ("О проекте…", "жоба") and compilations, hide amending acts, include texts whose act could not
be identified, kind of act, year of adoption. The thumbs up/down under a result appends a judgment to `data/app/feedback.jsonl`
(query, article, label), which can be used as more relevance data.

## How well does it work

On the project's test set of 45 everyday questions (judgments still to be reviewed by the author), the correct article is among the
first ten results for about 80% of Russian questions, 73% of Kazakh and 71% of English questions with the default
semantic method; BM25 manages 42% (Russian) and 31% (Kazakh) and cannot handle English. Details and caveats:
`docs/results_retrieval.md`.

## Limits

* Reference information, not legal advice. Texts are the corpus snapshot of 01.04.2024; laws change.
* Only articles are searched (codes and laws). Regulations without article structure are not covered by this index.
* The link opens the whole act; a link to the exact article is not offered because the official site renders text with JavaScript.
* About 6% of articles belong to texts that could not be matched to an act in the metadata; they show the file name as the title.
* The English and Kazakh interfaces are not translated: the page itself is in Russian.
* Bills written in Kazakh are recognised by keywords in the title ("жоба", "әзірлеген"), which is heuristic.
