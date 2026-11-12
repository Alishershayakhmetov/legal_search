"""Pick golden queries: questions whose judged answer the current engine returns in the top 5 (default filters).

They are a regression guard, not a quality measure: after any change of the index or the ranking the same questions must still
return the same articles. Writes annotation/golden_queries.json; tests/test_golden.py checks it (RUN_GOLDEN=1).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from engine import SearchEngine  # noqa: E402

TOP = 5
QUOTA = {"ru": 11, "kk": 5, "en": 4}
REFERENCES = [("статья 1 конституции рк", "Конституция Республики Казахстан", "1", "ru"), ("ст. 188 УК", "Уголовный кодекс Республики Казахстан", "188", "ru"),
              ("ст. 113 Трудового кодекса Республики Казахстан", "Трудовой кодекс Республики Казахстан", "113", "ru")]


def main():
    ann = ROOT / "annotation"
    needs = {n["id"]: n for n in json.loads((ann / "needs.json").read_text(encoding="utf-8"))}
    qrels = json.loads((ann / "qrels_v1.json").read_text(encoding="utf-8"))
    engine = SearchEngine()
    golden, topics_seen = [], {lang: set() for lang in QUOTA}
    for nid, items in qrels.items():
        n = needs[nid]
        gold = [j for j in items if j["grade"] == 2 and j["article_no"] is not None]
        if n["type"] == "title" or not gold:
            continue
        for lang in QUOTA:
            if sum(g["lang"] == lang for g in golden if not g["id"].startswith("ref")) >= QUOTA[lang] or n["topic"] in topics_seen[lang]:
                continue
            hits, _ = engine.search(n[lang], TOP, "dense")
            found = [(h.title.lower(), h.article_no) for h in hits]
            match = next((j for j in gold if (j["family"], j["article_no"]) in found), None)
            if match:
                topics_seen[lang].add(n["topic"])
                title = next(h.title for h in hits if h.title.lower() == match["family"] and h.article_no == match["article_no"])
                golden.append({"id": f"{nid}-{lang}", "query": n[lang], "lang": lang, "expect_title": title, "expect_article": match["article_no"], "top": TOP})
    for q, title, art, lang in REFERENCES:
        hits, _ = engine.search(q, TOP, "dense")
        if hits and hits[0].title == title and hits[0].article_no == art:
            golden.append({"id": f"ref-{art}", "query": q, "lang": lang, "expect_title": title, "expect_article": art, "top": 1})
    (ann / "golden_queries.json").write_text(json.dumps(golden, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(golden), "golden queries:", {lang: sum(g["lang"] == lang for g in golden) for lang in QUOTA})


if __name__ == "__main__":
    main()
