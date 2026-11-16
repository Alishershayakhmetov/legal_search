"""A1: quality and faithfulness of the cited answer, measured on the 45 situation/concept needs per language.

For each question the app's pipeline runs (default filters, 4 excerpts, local model from app/llm.py) with the semantic threshold switched off, so the
raw checks can be studied afterwards. Reported: how often the model abstains, how many answer sentences cite a missing excerpt, cite no excerpt or contain a
number that is not in the cited excerpt, the distribution of the semantic support score for the true citation against a control (the same sentence checked
against excerpts of other questions), whether a gold article was among the excerpts, and all answers for a manual read (outputs/answers_sample.json).
Output: outputs/answer_eval.json. Usage: python src/46_answer_eval.py [lang ...]
"""
import json
import random
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import answer as A  # noqa: E402
import llm  # noqa: E402
from engine import Filters, SearchEngine  # noqa: E402

FAMILY = re.compile(r"[«»\"“”„]")


def family(title):
    return FAMILY.sub("", (title or "").lower()).strip()


def main():
    langs = sys.argv[1:] or ["ru", "kk", "en"]
    qrels = json.loads((ROOT / "annotation" / "qrels_v1.json").read_text(encoding="utf-8"))
    queries = [json.loads(line) for line in open(ROOT / "annotation" / "queries.jsonl", encoding="utf-8")]
    queries = [q for q in queries if q["type"] in ("situation", "concept") and q["lang"] in langs]
    eng = SearchEngine()
    _ = eng.model
    embed = lambda xs: eng.model.encode(xs, normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    backend = llm.get_backend()
    rng = random.Random(3)
    store = []
    pool = {}  # excerpts of every question, for the control
    for q in queries:
        lang = q["lang"]
        hits, info = eng.search(q["text"], 6, "dense", Filters())
        pick = lambda h, lang=lang: h.texts.get("kk" if lang == "kk" and "kk" in h.texts else "ru", "")
        ex = A.select_excerpts(hits, q["text"], pick, eng.explain)
        gold = {(g["family"], g["article_no"]) for g in qrels.get(q["need_id"], []) if g["grade"] == 2 and g["article_no"] is not None}
        in_ex = [(family(e["title"]), e["article_no"]) in gold for e in ex]
        res = A.make_answer(q["text"], lang, ex, backend, embed, tau=-1.0)
        res.update(query_id=q["query_id"], lang=lang, query=q["text"], low_confidence=bool(info.get("low_confidence")), gold_in_excerpts=any(in_ex),
                   gold_excerpt_numbers=[i + 1 for i, g in enumerate(in_ex) if g], excerpt_texts={e["n"]: e["text"] for e in ex})
        store.append(res)
        pool[q["query_id"]] = ex
        print(q["query_id"], res["status"], res["seconds"], flush=True)

    summary = {}
    for lang in langs:
        rows = [r for r in store if r["lang"] == lang]
        sents = [(r, s) for r in rows for s in r["sentences"]]
        ctrl, true = [], []
        for r, s in sents:
            if not s["cites"] or s.get("support") is None:
                continue
            true.append(s["support"])
            others = [e for k, ex in pool.items() if k != r["query_id"] and k.endswith(lang) for e in ex]
            sample = rng.sample(others, 3)
            body = A.CITE.sub("", s["text"]).strip()
            cand = [x for e in sample for x in re.split(r"(?<=[.;:])\s+|\n+", e["text"]) if len(x.strip()) >= 15]
            m = embed([body] + cand)
            ctrl.append(float((m[1:] @ m[0]).max()))
        summary[lang] = {
            "questions": len(rows), "abstain": sum(r["status"] == "abstain" for r in rows), "answered": sum(r["status"] != "abstain" for r in rows),
            "low_confidence_questions": sum(r["low_confidence"] for r in rows),
            "gold_in_excerpts": sum(r["gold_in_excerpts"] for r in rows),
            "sentences": len(sents),
            "no_citation": sum("нет ссылки на выдержку" in s["reasons"] for _, s in sents),
            "missing_excerpt": sum("ссылка на несуществующую выдержку" in s["reasons"] for _, s in sents),
            "number_not_in_excerpt": sum(any(x.startswith("числа нет") for x in s["reasons"]) for _, s in sents),
            "support_true": {k: round(float(v), 3) for k, v in zip(("min", "p5", "p25", "median", "p75"), np.percentile(true, [0, 5, 25, 50, 75]))} if true else None,
            "support_control": {k: round(float(v), 3) for k, v in zip(("median", "p75", "p95", "p99", "max"), np.percentile(ctrl, [50, 75, 95, 99, 100]))} if ctrl else None,
            "answered_with_gold_cited": sum(
                1 for r in rows if r["status"] != "abstain" and set(r["gold_excerpt_numbers"]) & {n for s in r["sentences"] for n in s["cites"]}),
        }
    old_eval, old_store = {}, []
    if (ROOT / "outputs" / "answer_eval.json").exists() and set(langs) != {"ru", "kk", "en"}:  # a partial run replaces only its own languages
        old_eval = json.loads((ROOT / "outputs" / "answer_eval.json").read_text(encoding="utf-8"))["summary"]
        old_store = [r for r in json.loads((ROOT / "outputs" / "answers_sample.json").read_text(encoding="utf-8")) if r["lang"] not in langs]
    summary = {**old_eval, **summary}
    store = old_store + store
    (ROOT / "outputs" / "answer_eval.json").write_text(json.dumps({"model": f"{backend.name}:{backend.model}", "summary": summary}, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "outputs" / "answers_sample.json").write_text(json.dumps(store, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
