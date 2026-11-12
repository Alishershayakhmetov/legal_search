"""Evaluate dense retrieval, BM25 and their hybrid on the query set.

usage: 25_dense_eval.py MODEL SCOPE [--bm25-mode MODE]
"""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402
from evaluate import SUFFIX, build_units, evaluate, load_queries, summarize  # noqa: E402
from search_lib import build_searchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
QUERY_PREFIX = {"intfloat/multilingual-e5-small": "query: ", "intfloat/multilingual-e5-base": "query: "}
RRF_K = 60


def short(name):
    return name.split("/")[-1]


def load_embeddings(name, scope):
    d = ROOT / "data" / "index" / f"emb_{short(name)}_{scope}"
    parts = sorted(d.glob("part_*.npy"))
    emb = torch.from_numpy(np.concatenate([np.load(p) for p in parts])).to("cuda")
    return emb, np.load(d / "doc_ids.npy")


class Dense:
    def __init__(self, name, scope, docs):
        self.name = name
        self.emb, self.ids = load_embeddings(name, scope)
        self.lang = docs.lang.to_numpy()[self.ids]
        self.mask = {l: torch.from_numpy(self.lang == l).to("cuda") for l in ("ru", "kk")}
        self.model = SentenceTransformer(name, device="cuda", model_kwargs={"torch_dtype": torch.float16})
        self.prefix = QUERY_PREFIX.get(name, "")

    def search(self, text, lang=None, k=100):
        q = self.model.encode([self.prefix + text], normalize_embeddings=True, convert_to_tensor=True).half()
        scores = (self.emb @ q[0]).float()
        if lang in self.mask:
            scores = scores.masked_fill(~self.mask[lang], -1e4)
        top = torch.topk(scores, k).indices.cpu().numpy()
        return self.ids[top]


def rrf(lists, k=100):
    score = {}
    for lst in lists:
        for r, d in enumerate(lst):
            score[d] = score.get(d, 0.0) + 1.0 / (RRF_K + r + 1)
    return np.array(sorted(score, key=score.get, reverse=True)[:k])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("scope", choices=["articles", "all"])
    ap.add_argument("--bm25-mode", default="stem")
    args = ap.parse_args()

    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "lang", "text_hash", "law_id", "is_article", "text"])
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    translated = json.loads((ROOT / "annotation" / "queries_en_translated.json").read_text(encoding="utf-8")) if (ROOT / "annotation" / "queries_en_translated.json").exists() else {}

    dense = Dense(args.model, args.scope, docs)
    sub_all = docs[docs.is_article] if args.scope == "articles" else docs
    bm25 = {}
    for lang in ("ru", "kk"):
        sub = sub_all[sub_all.lang == lang]
        mode = args.bm25_mode if lang == "ru" else ("p5" if args.bm25_mode == "stem" else args.bm25_mode)
        bm25[lang] = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("bm25",), log=lambda m: None)["bm25"]

    def native(q, system):
        lang, text = q["lang"], q["text"]
        if system == "bm25":
            return bm25[lang].search(text, 100)[0]
        if system == "dense":
            return dense.search(text, lang)
        if system == "dense_cross":
            return dense.search(text)
        if system == "hybrid":
            return rrf([bm25[lang].search(text, 100)[0], dense.search(text, lang)])
        raise ValueError(system)

    def english(q, system):
        qid, text = q["query_id"], q["text"]
        tr = translated.get(qid, {})
        if system == "dense_cross":  # strategy A: the English query against Russian and Kazakh passages directly
            return dense.search(text)
        if system == "bm25_translated" and tr:  # strategy B: translate, then lexical search in each language
            return rrf([bm25["ru"].search(tr["ru"], 100)[0], bm25["kk"].search(tr["kk"], 100)[0]])
        if system == "dense_translated" and tr:
            return rrf([dense.search(tr["ru"], "ru"), dense.search(tr["kk"], "kk")])
        if system == "hybrid_translated" and tr:
            return rrf([bm25["ru"].search(tr["ru"], 100)[0], bm25["kk"].search(tr["kk"], 100)[0],
                        dense.search(tr["ru"], "ru"), dense.search(tr["kk"], "kk"), dense.search(text)])
        return np.array([], dtype=np.int64)

    rows = []
    plan = [("ru", ["bm25", "dense", "dense_cross", "hybrid"]), ("kk", ["bm25", "dense", "dense_cross", "hybrid"]),
            ("en", ["dense_cross", "bm25_translated", "dense_translated", "hybrid_translated"])]
    for lang, systems in plan:
        qs = [q for q in queries if q["lang"] == lang]
        for system in systems:
            if lang == "en" and system != "dense_cross" and not translated:
                continue
            fn = (lambda text, _l, system=system: None)
            per_q = []
            t0 = time.time()
            from evaluate import first_ranks, query_metrics
            for q in qs:
                ranked = (english if lang == "en" else native)(q, system)[:100]
                found = first_ranks(ranked, units[q["need_id"]], doc_hash, doc_law)
                per_q.append({"query_id": q["query_id"], "need_id": q["need_id"], "lang": lang, "type": q["type"], **query_metrics(found, units[q["need_id"]])})
            ms = (time.time() - t0) / len(qs) * 1000
            summ = summarize(per_q, boot=500)
            r = {"model": short(args.model), "scope": args.scope, "lang": lang, "system": system, "ms_per_query": round(ms),
                 **{k: round(float(v[0]), 3) for k, v in summ.items()}, "mrr_ci": [round(float(summ["mrr@10"][1]), 3), round(float(summ["mrr@10"][2]), 3)]}
            rows.append(r)
            print(f"{lang} {system:18s} S@1 {r['success@1']:.2f} S@5 {r['success@5']:.2f} S@10 {r['success@10']:.2f} R@50 {r['recall@50']:.2f} "
                  f"MRR {r['mrr@10']:.3f} {r['mrr_ci']} nDCG {r['ndcg@10']:.3f} | {ms:.0f} ms/q", flush=True)
    out = ROOT / "outputs" / f"dense_results_{short(args.model)}_{args.scope}{SUFFIX}.json"
    out.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
