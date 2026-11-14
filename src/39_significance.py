"""Paired significance tests (E5) and breakdown by query type and branch of law (E6), judgments v1, article scope.

Per-query Success@10 and MRR@10 are computed once for every system; the difference between two systems on the same
needs is bootstrapped (resampling needs, 10,000 times) and, for Success@10, tested with an exact sign test on the
discordant needs. Output: outputs/significance.json.
"""
import importlib.util
import json
import os
import sys
from math import comb
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("QRELS_VERSION", "v1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402
from evaluate import build_units, first_ranks, load_queries, query_metrics  # noqa: E402
from search_lib import build_searchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("de", Path(__file__).with_name("25_dense_eval.py"))
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)

MODELS = {"e5-small": "intfloat/multilingual-e5-small", "e5-base": "intfloat/multilingual-e5-base", "bge-m3": "BAAI/bge-m3"}
BOOT = 10_000


def sign_test_p(a_only, b_only):
    """Two-sided exact binomial p-value of the discordant pairs under 'both systems are equally good'."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    k = min(a_only, b_only)
    return min(1.0, 2 * sum(comb(n, i) for i in range(k + 1)) / 2 ** n)


def paired(a, b, rng):
    """a, b: per-need arrays (same order). Mean difference a-b with a bootstrap interval."""
    d = a - b
    idx = rng.integers(0, len(d), (BOOT, len(d)))
    bs = d[idx].mean(axis=1)
    return float(d.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


def main():
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "lang", "text_hash", "law_id", "is_article", "text"])
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    needs = {n["id"]: n for n in json.loads((ROOT / "annotation" / "needs.json").read_text(encoding="utf-8"))}
    translated = json.loads((ROOT / "annotation" / "queries_en_translated.json").read_text(encoding="utf-8"))
    art = docs[docs.is_article]
    bm25 = {}
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        sub = art[art.lang == lang]
        bm25[lang] = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("bm25",), log=lambda m: None)["bm25"]

    runs = {}  # (lang, system) -> {need_id: ranked ids}
    for key, name in MODELS.items():
        dense = de.Dense(name, "articles", docs)
        for q in queries:
            lang, nid, text = q["lang"], q["need_id"], q["text"]
            if lang in ("ru", "kk"):
                runs.setdefault((lang, key), {})[nid] = dense.search(text, lang)
                if key == "bge-m3":
                    runs.setdefault((lang, "bm25"), {})[nid] = bm25[lang].search(text, 100)[0]
                    runs.setdefault((lang, "hybrid"), {})[nid] = de.rrf([bm25[lang].search(text, 100)[0], dense.search(text, lang)])
            elif key == "bge-m3":
                tr = translated[q["query_id"]]
                runs.setdefault(("en", "cross"), {})[nid] = dense.search(text)
                runs.setdefault(("en", "translated"), {})[nid] = de.rrf([dense.search(tr["ru"], "ru"), dense.search(tr["kk"], "kk")])
                runs.setdefault(("en", "hybrid_translated"), {})[nid] = de.rrf([
                    bm25["ru"].search(tr["ru"], 100)[0], bm25["kk"].search(tr["kk"], 100)[0],
                    dense.search(tr["ru"], "ru"), dense.search(tr["kk"], "kk"), dense.search(text)])
        del dense
        import torch
        torch.cuda.empty_cache()

    per = {}  # (lang, system) -> DataFrame need_id, s10, mrr
    for (lang, system), by_need in runs.items():
        rows = []
        for nid, ranked in by_need.items():
            m = query_metrics(first_ranks(ranked[:100], units[nid], doc_hash, doc_law), units[nid])
            rows.append({"need_id": nid, "s10": m["success@10"], "mrr": m["mrr@10"]})
        per[(lang, system)] = pd.DataFrame(rows).sort_values("need_id").reset_index(drop=True)

    rng = np.random.default_rng(0)
    comparisons = {"ru": [("bge-m3", "bm25"), ("bge-m3", "e5-base"), ("bge-m3", "e5-small"), ("bge-m3", "hybrid"), ("e5-base", "bm25"), ("e5-small", "bm25")],
                   "kk": [("bge-m3", "bm25"), ("bge-m3", "e5-base"), ("bge-m3", "e5-small"), ("bge-m3", "hybrid"), ("e5-base", "bm25"), ("e5-small", "bm25")],
                   "en": [("cross", "translated"), ("cross", "hybrid_translated"), ("hybrid_translated", "translated")]}
    tests = []
    for lang, pairs in comparisons.items():
        for a, b in pairs:
            da, db = per[(lang, a)], per[(lang, b)]
            assert (da.need_id == db.need_id).all()
            s_a, s_b = da.s10.to_numpy(), db.s10.to_numpy()
            m10, lo10, hi10 = paired(s_a, s_b, rng)
            mm, lom, him = paired(da.mrr.to_numpy(), db.mrr.to_numpy(), rng)
            a_only, b_only = int(((s_a == 1) & (s_b == 0)).sum()), int(((s_a == 0) & (s_b == 1)).sum())
            tests.append({"lang": lang, "a": a, "b": b, "n": len(da), "s10_a": round(float(s_a.mean()), 3), "s10_b": round(float(s_b.mean()), 3),
                          "s10_diff": [round(m10, 3), round(lo10, 3), round(hi10, 3)], "a_only": a_only, "b_only": b_only,
                          "sign_p": round(sign_test_p(a_only, b_only), 4),
                          "mrr_diff": [round(mm, 3), round(lom, 3), round(him, 3)]})
    breakdown = {}
    for lang in ("ru", "kk", "en"):
        system = "cross" if lang == "en" else "bge-m3"
        d = per[(lang, system)].assign(type=lambda x: x.need_id.map(lambda n: needs[n]["type"]), topic=lambda x: x.need_id.map(lambda n: needs[n]["topic"]))
        for col in ("type", "topic"):
            g = d.groupby(col).agg(n=("s10", "size"), s10=("s10", "mean"), mrr=("mrr", "mean")).round(3)
            breakdown.setdefault(lang, {})[col] = {k: v for k, v in g.to_dict("index").items()}
    out = {"qrels": "v1", "boot": BOOT, "n_needs": {f"{l}/{s}": len(d) for (l, s), d in per.items()}, "tests": tests, "breakdown": breakdown,
           "per_need": {f"{l}/{s}": d.set_index("need_id")[["s10", "mrr"]].round(3).to_dict("index") for (l, s), d in per.items()}}
    (ROOT / "outputs" / "significance.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for t in tests:
        print(f"{t['lang']} {t['a']:>17s} vs {t['b']:<17s} S@10 {t['s10_a']:.2f} vs {t['s10_b']:.2f} diff {t['s10_diff']} only-a {t['a_only']} only-b {t['b_only']} p={t['sign_p']} | MRR diff {t['mrr_diff']}")
    print(json.dumps(breakdown, ensure_ascii=False))


if __name__ == "__main__":
    main()
