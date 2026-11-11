# Query test set: annotation guidelines

The test set measures how well the search finds the legal provision that answers a person's question.
It is built from **information needs**. Each need is written once as a situation, then expressed as
three queries (Russian, Kazakh, English) that share the same relevance judgments.

## What is judged

A judgment is a triple `(query need, document family, article)`:

* **Document family**: all versions of one act. A code, its "Компиляция …" copy and its "О проекте …"
  drafts are one family (`family_key` in `src/annotation_tools.py`). A hit on any version counts, so
  a system is not punished for returning a draft that contains the same article text.
* **Article**: the article number inside the family. Acts without articles are judged at act level
  (`article = null`).

The same judgments serve all three query languages, because Russian and Kazakh texts of an act use the
same article numbers. Judgments are checked against the Russian text first; the Kazakh article is
looked up by the same number and must be the same provision.

## Relevance scale

| Grade | Meaning | Test |
|---|---|---|
| 2 | Answers the question | A person reading only this article could act on it |
| 1 | Related | Same topic or a necessary condition, but does not answer by itself |
| 0 | Not relevant | Everything else |

Recall@k and MRR count grade 2 as relevant; nDCG uses both grades. Only grades 1 and 2 are stored.

## Query types

| Type | Share | Example need | Goal |
|---|---|---|---|
| `situation` | ~70% | "Employer has not paid salary for two months" | Everyday wording, no legal terms |
| `concept` | ~15% | "General limitation period for a claim" | Direct legal question |
| `title` | ~15% | "Law on personal data" | Find an act by name (title layer) |

## Writing rules (to avoid a test set that only rewards keyword matching)

1. Describe the situation as a layperson would. Do not copy the article heading or its distinctive words.
2. One need, one intent. No two questions in one query.
3. Kazakh and English queries are written as natural queries, not word-for-word translations of the
   Russian one. They must express the same need.
4. No query may name an article number.
5. Needs span the main branches of law (labour, civil, family, tax, administrative, criminal,
   procedure, land and housing, business, social, other) so one code does not dominate.

## Procedure

1. A need is drafted with the act and heading it is expected to hit (`anchors` in `needs.json`).
2. The anchor is looked up in the corpus and the **article text is read** to confirm it answers the need.
3. Candidates are added by pooling: the top results of several systems are judged. Version 0 is pooled
   from a TF-IDF search; dense and hybrid systems are added to the pool when they exist, so the
   test set does not favour the first system that produced it.
4. A second person (the project author) reviews every judgment in `annotation/review.html` and
   confirms, changes or removes it. Only reviewed judgments enter the final evaluation.

## Known limits

* Drafted by an AI assistant, not by a lawyer. The author's review is required before any number is reported.
* Kazakh queries need a native-speaker check.
* Pooling from one system biases the set toward it; this is reduced, not removed, by adding pools later.
* Laws change: judgments refer to the corpus snapshot of 01.04.2024 (Mendeley release).
