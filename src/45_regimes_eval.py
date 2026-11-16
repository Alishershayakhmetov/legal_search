"""A13: what does the "compare acts" view (one best article per act, top 5 acts) add to the plain article list?

For the 45 situation/concept needs per language: share of needs whose judged answer (grade 2) is (a) among the top 5 articles of the
plain list, (b) among the best articles of the top 5 acts, (c) in an act that appears among the top 5 acts (act-level hit, the answer
may be another article of that act). Same engine, default filters, no prior. Output: outputs/regimes.json.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from engine import SearchEngine, group_by_act  # noqa: E402

FAMILY = re.compile(r"[«»\"“”„]")


def family(title):
    return FAMILY.sub("", (title or "").lower()).strip()


def main():
    qrels = json.loads((ROOT / "annotation" / "qrels_v1.json").read_text(encoding="utf-8"))
    queries = [json.loads(line) for line in open(ROOT / "annotation" / "queries.jsonl", encoding="utf-8")]
    queries = [q for q in queries if q["type"] in ("situation", "concept")]
    eng = SearchEngine()
    _ = eng.model
    res = {}
    for q in queries:
        gold = [(j["family"], j["article_no"]) for j in qrels.get(q["need_id"], []) if j["grade"] == 2 and j["article_no"] is not None]
        if not gold:
            continue
        hits, _ = eng.search(q["text"], 40, "dense")
        plain = [(family(h.title), h.article_no) for h in hits[:5]]
        rows = group_by_act(hits, 5)
        best = [(family(h.title), h.article_no) for h, _ in rows]
        acts = {family(h.title) for h, _ in rows}
        r = res.setdefault(q["lang"], {"n": 0, "plain5": 0, "regimes_article": 0, "regimes_act": 0, "acts_shown": 0, "plain_distinct_acts": 0})
        r["n"] += 1
        r["plain5"] += any(g in plain for g in gold)
        r["regimes_article"] += any(g in best for g in gold)
        r["regimes_act"] += any(g[0] in acts for g in gold)
        r["acts_shown"] += len(rows)
        r["plain_distinct_acts"] += len({p[0] for p in plain})
    for lang, r in res.items():
        r["mean_acts_shown"] = round(r.pop("acts_shown") / r["n"], 2)
        r["mean_distinct_acts_in_plain_top5"] = round(r.pop("plain_distinct_acts") / r["n"], 2)
    (ROOT / "outputs" / "regimes.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(res, ensure_ascii=False, indent=1))
    hits, _ = eng.search("Сколько дней отпуска положено?", 40, "dense")
    for h, n in group_by_act(hits, 5):
        print(h.title[:60], "ст.", h.article_no, "+", n)


if __name__ == "__main__":
    main()
