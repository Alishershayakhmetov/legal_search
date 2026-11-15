"""S14: can the app decide by itself between "find an act by name" and "find an article for a question"?

For the 24 title queries (8 needs x ru/kk/en) and the 135 situation/concept queries the engine's top title similarity, top article
similarity and the number of words are collected; AUC of each feature and the accuracy of the rule used by the app are reported.
The rule's threshold is read from the same queries, so its accuracy on new questions is not confirmed. Output: outputs/router.json.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score

os.environ.setdefault("QRELS_VERSION", "v1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "app"))
from engine import Filters, SearchEngine, route_query  # noqa: E402
from evaluate import load_queries  # noqa: E402


def main():
    queries = load_queries()
    eng = SearchEngine()
    _ = eng.model
    mask = eng.mask(Filters())
    rows = []
    for q in queries:
        t, _ = eng.search_titles(q["text"], 1, Filters())
        a_rows, a_sc = eng._dense_rows(q["text"], mask, 5)
        rows.append({"lang": q["lang"], "title": q["type"] == "title", "t_score": t[0]["score"], "a_score": float(a_sc[0]),
                     "words": len(q["text"].split()), "text": q["text"], "routed": route_query(q["text"], t[0]["score"], float(a_sc[0]))})
    out = {"auc": {}, "accuracy": {}, "errors": [], "rows": [{k: (round(r[k], 4) if isinstance(r[k], float) else r[k]) for k in ("lang", "title", "t_score", "a_score", "words")} for r in rows]}
    y = np.array([r["title"] for r in rows])
    for feat, sign in (("t_score", 1), ("a_score", -1), ("words", -1)):
        out["auc"][feat] = round(float(roc_auc_score(y, sign * np.array([r[feat] for r in rows]))), 3)
    out["auc"]["t_minus_a"] = round(float(roc_auc_score(y, np.array([r["t_score"] - r["a_score"] for r in rows]))), 3)
    for lang in ("ru", "kk", "en", "all"):
        sub = [r for r in rows if lang == "all" or r["lang"] == lang]
        ok = [(r["routed"] == "titles") == r["title"] for r in sub]
        out["accuracy"][lang] = {"n": len(sub), "correct": int(sum(ok)), "title_recall": round(float(np.mean([r["routed"] == "titles" for r in sub if r["title"]])), 3),
                                 "question_to_articles": round(float(np.mean([r["routed"] == "articles" for r in sub if not r["title"]])), 3)}
    out["errors"] = [{k: r[k] for k in ("lang", "title", "t_score", "a_score", "words", "text", "routed")} for r in rows if (r["routed"] == "titles") != r["title"]]
    (ROOT / "outputs" / "router.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: out[k] for k in ("auc", "accuracy")}, ensure_ascii=False))
    for tt in (True, False):
        d = sorted(round(r["t_score"] - r["a_score"], 3) for r in rows if r["title"] == tt and r["words"] <= 7)
        print("title" if tt else "other", "t-a (words<=7):", d)
    for e in out["errors"]:
        print(e)
    for name, sub in (("title", [r for r in rows if r["title"]]), ("other", [r for r in rows if not r["title"]])):
        print(name, "t_score min/median/max", [round(float(f(np.array([r["t_score"] for r in sub]))), 3) for f in (np.min, np.median, np.max)],
              "words median", int(np.median([r["words"] for r in sub])))


if __name__ == "__main__":
    main()
