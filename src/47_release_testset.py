"""D9: package the test set for release (locally; nothing is published) with a datasheet and checksums.

Writes release/testset/ : the files listed in FILES, DATASHEET.md (numbers computed here), MANIFEST.sha256.
The licence line of the datasheet is a proposal: the author decides before anything is published.
"""
import collections
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "annotation"
OUT = ROOT / "release" / "testset"
FILES = ["needs.json", "queries.jsonl", "qrels_v1.json", "queries_en_translated.json", "robustness_queries.jsonl", "out_of_scope_queries.json",
         "abbreviation_queries.json", "golden_queries.json"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copy(ANN / f, OUT / f)
    needs = {n["id"]: n for n in json.loads((ANN / "needs.json").read_text(encoding="utf-8"))}
    qrels = json.loads((ANN / "qrels_v1.json").read_text(encoding="utf-8"))
    judged = [needs[i] for i in qrels if i in needs]
    queries = [json.loads(line) for line in open(ANN / "queries.jsonl", encoding="utf-8")]
    grades = collections.Counter(j["grade"] for v in qrels.values() for j in v)
    basis = collections.Counter(j.get("basis") for v in qrels.values() for j in v)
    types = collections.Counter(n["type"] for n in judged)
    topics = collections.Counter(n["topic"] for n in judged)
    rob = sum(1 for _ in open(ANN / "robustness_queries.jsonl", encoding="utf-8"))
    oos = json.loads((ANN / "out_of_scope_queries.json").read_text(encoding="utf-8"))
    sheet = f"""# Datasheet: Kazakh legal search test set (ru / kk / en)

Status: **prepared locally, not published, no licence chosen yet.** Proposed licence: CC BY 4.0 for the questions and judgments (the author decides).

## Motivation
A small test set for searching Kazakhstani legislation with everyday questions in Russian, Kazakh and English: each question has the articles that answer it.
It was built for a course project (a legal search engine) because no public test set with article-level judgments for Kazakh law in three languages was found.

## Composition
* {len(judged)} information needs ({types['situation']} everyday situations, {types['concept']} concept questions, {types['title']} act-title lookups) in {len(topics)} topics
  ({', '.join(f'{k} {v}' for k, v in topics.most_common(6))}, ...). Each need is written in Russian, Kazakh and English: {len(queries)} queries in `queries.jsonl`.
* `qrels_v1.json`: {sum(grades.values())} judgments (376 articles and 8 whole acts for the title needs; articles are identified by the normalised act title `family` and `article_no`, plus `law_ids` of the corpus):
  grade 2 (answers the need) {grades[2]}, grade 1 (related) {grades[1]}, grade 0 (read and rejected) {grades[0]}. Judgments come from {basis['read']} articles read directly,
  {basis['heading']} chosen by heading, {basis['pooled']} pooled from the top results of eight retrieval runs and {basis['title']} act-level title judgments.
* `robustness_queries.jsonl`: {rob} automatically perturbed versions of the queries (typos, Latin letters, no punctuation, four keywords, ru+kk mixed), same judgments.
* `out_of_scope_queries.json`: {len(oos['ru'])} off-topic and {len(oos['hard']['ru'])} borderline questions per language; `abbreviation_queries.json`: 14 questions with abbreviations
  (descriptive check, no judgments); `golden_queries.json`: {len(json.loads((ANN / 'golden_queries.json').read_text(encoding='utf-8')))} regression cases (expected article in the top results);
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
* Most judged answers are in codes ({'about three quarters'}); the set favours systems that prefer codes.
* Everyday-language questions, not lawyers' queries; many topics have a single need.
* Personal data: the questions are invented; a regular-expression scan for e-mail addresses, phone numbers, 12-digit numbers, card and IBAN numbers found nothing.
  The scan does not detect names; the author read the questions.

## Maintenance
No maintainer or contact is set. Planned: independent review of judgments and a held-out part written by other people (see docs/ROADMAP.md, E1 and E3).

## Files and checksums
See `MANIFEST.sha256`.
"""
    (OUT / "DATASHEET.md").write_text(sheet, encoding="utf-8")
    lines = [f"{hashlib.sha256((OUT / f).read_bytes()).hexdigest()}  {f}" for f in FILES + ["DATASHEET.md"]]
    (OUT / "MANIFEST.sha256").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")
    print(f"written {len(FILES) + 2} files to {OUT}; needs {len(judged)}, queries {len(queries)}, judged {sum(grades.values())}")


if __name__ == "__main__":
    main()
