# Datasheet: Kazakh legal search test set (ru / kk / en)

Status: **prepared locally, not published, no licence chosen yet.** Proposed licence: CC BY 4.0 for the questions and judgments (the author decides).

## Motivation
A small test set for searching Kazakhstani legislation with everyday questions in Russian, Kazakh and English: each question has the articles that answer it.
It was built for a course project (a legal search engine) because no public test set with article-level judgments for Kazakh law in three languages was found.

## Composition
* 53 information needs (30 everyday situations, 15 concept questions, 8 act-title lookups) in 19 topics
  (title 8, labour 7, civil 4, family 4, tax 4, admin 4, ...). Each need is written in Russian, Kazakh and English: 159 queries in `queries.jsonl`.
* `qrels_v1.json`: 384 judgments (376 articles and 8 whole acts for the title needs; articles are identified by the normalised act title `family` and `article_no`, plus `law_ids` of the corpus):
  grade 2 (answers the need) 75, grade 1 (related) 100, grade 0 (read and rejected) 209. Judgments come from 58 articles read directly,
  48 chosen by heading, 270 pooled from the top results of eight retrieval runs and 8 act-level title judgments.
* `robustness_queries.jsonl`: 810 automatically perturbed versions of the queries (typos, Latin letters, no punctuation, four keywords, ru+kk mixed), same judgments.
* `out_of_scope_queries.json`: 20 off-topic and 6 borderline questions per language; `abbreviation_queries.json`: 14 questions with abbreviations
  (descriptive check, no judgments); `golden_queries.json`: 23 regression cases (expected article in the top results);
  `queries_en_translated.json`: machine translations (NLLB-200) of the English queries into Russian and Kazakh, used by one baseline.
* No article text is included. Articles are referenced by act title and article number; short headings in `qrels_v1.json` are copied from the source texts.

## Collection process
Questions were drafted by an AI assistant (Claude) together with the course author, covering everyday legal topics, and translated between the three languages by the assistant.
Relevant articles were found by searching the corpus, reading candidates and, for round 2, judging the pooled top results of eight systems. **No lawyer and no second
annotator reviewed the judgments**; the Kazakh queries were not checked by a native speaker. All numbers computed on this set are therefore provisional.

## Source data and its licences
Judgments refer to the corpora used by the project: the Mendeley dataset "Textual Foundations of Justice: Kazakhstani laws and jurisprudence dataset" (texts, CC BY 4.0,
as shown on its page when downloaded) and the KazakhLawCorpus metadata on Hugging Face (**licence not verified; check its card before release**). Official texts: adilet.zan.kz.
The texts are a snapshot of 01.04.2024; later amendments are not reflected, so some judged articles may have changed.

## Intended uses
Comparing retrieval methods for Kazakhstani legal text; studying robustness (typos, transliteration) and abstention on off-topic questions. **Not** for legal advice, and not
for training or evaluating systems that claim to give legal conclusions.

## Known limitations
* Small (45 situation/concept needs per language): differences of a few points are noise; intervals are wide.
* Judgments are incomplete (pooling covers eight systems; relevant articles outside their results are missing), so scores are lower bounds.
* Most judged answers are in codes (about three quarters); the set favours systems that prefer codes.
* Everyday-language questions, not lawyers' queries; many topics have a single need.
* Personal data: the questions are invented; a regular-expression scan for e-mail addresses, phone numbers, 12-digit numbers, card and IBAN numbers found nothing.
  The scan does not detect names; the author read the questions.

## Maintenance
No maintainer or contact is set. Planned: independent review of judgments and a held-out part written by other people (see docs/ROADMAP.md, E1 and E3).

## Files and checksums
See `MANIFEST.sha256`.
