"""S25: do larger or newer encoders beat bge-m3? Re-ranking comparison on a candidate pool (not a full-corpus run).

Re-embedding 319k articles takes 1-2 hours per model on this laptop, so each model re-ranks the same candidate pool per question instead: the union of the
top 150 of bge-m3, the top 100 of multilingual-e5-base and the top 100 of BM25 (not for English) over the article index. Metrics are computed on the
pool ranking with the same judgments (v1) and the same unit matching as the other experiments. This measures re-ranking quality, not retrieval: the
pool is shaped by bge-m3, which favours it a little, and relevant articles outside the pool are missed by every model alike.
usage: python src/50_encoder_sweep.py MODEL [MODEL ...]        Output: outputs/encoder_sweep.json (merged across runs)
"""
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

os.environ.setdefault("QRELS_VERSION", "v1")
sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402
from evaluate import build_units, first_ranks, load_queries, query_metrics  # noqa: E402
from search_lib import build_searchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("de", Path(__file__).with_name("25_dense_eval.py"))
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)

PREFIX = {  # (query prefix, passage prefix)
    "BAAI/bge-m3": ("", ""),
    "intfloat/multilingual-e5-base": ("query: ", "passage: "),
    "intfloat/multilingual-e5-large": ("query: ", "passage: "),
    "Qwen/Qwen3-Embedding-0.6B": ("Instruct: Given a legal question, retrieve the article of Kazakhstani legislation that answers it" + chr(10) + "Query: ", ""),
}
TRUST = set()  # no model that needs downloaded code is used


def build_pool(docs, queries):
    cache = ROOT / "data" / "index" / "sweep_pool.json"
    if cache.exists():
        return {k: np.array(v) for k, v in json.loads(cache.read_text()).items()}
    art = docs[docs.is_article]
    bm25 = {}
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        sub = art[art.lang == lang]
        bm25[lang] = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("bm25",), log=lambda m: None)["bm25"]
    bge, e5 = de.Dense("BAAI/bge-m3", "articles", docs), de.Dense("intfloat/multilingual-e5-base", "articles", docs)
    pool = {}
    for q in queries:
        lang = None if q["lang"] == "en" else q["lang"]
        ids = list(bge.search(q["text"], lang, 150)) + list(e5.search(q["text"], lang, 100))
        if lang:
            ids += list(bm25[lang].search(q["text"], 100)[0])
        pool[q["query_id"]] = np.array(sorted(set(int(i) for i in ids)))
    del bge, e5
    torch.cuda.empty_cache()
    cache.write_text(json.dumps({k: v.tolist() for k, v in pool.items()}))
    return pool


def main():
    models = sys.argv[1:] or ["BAAI/bge-m3"]
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "lang", "text_hash", "law_id", "is_article", "text"])
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    pool = build_pool(docs, queries)
    sizes = [len(v) for v in pool.values()]
    print("pool per query: mean", int(np.mean(sizes)), "max", max(sizes), "| unique docs", len(set(np.concatenate(list(pool.values())).tolist())), flush=True)
    out_path = ROOT / "outputs" / "encoder_sweep.json"
    results = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}
    from sentence_transformers import SentenceTransformer
    all_ids = np.array(sorted(set(np.concatenate(list(pool.values())).tolist())))
    texts = docs.text.to_numpy()
    for name in models:
        t0 = time.time()
        kw = {"trust_remote_code": True} if name in TRUST else {}
        model = SentenceTransformer(name, device="cuda", model_kwargs={"torch_dtype": torch.float16}, **kw)
        model.max_seq_length = 384
        qp, pp = PREFIX[name]
        emb = model.encode([pp + texts[i] for i in all_ids], batch_size=16, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False).astype(np.float16)
        pos = {int(d): i for i, d in enumerate(all_ids)}
        t_docs = time.time() - t0
        per = []
        for q in queries:
            qe = model.encode([qp + q["text"]], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)[0]
            cand = pool[q["query_id"]]
            sc = emb[[pos[int(d)] for d in cand]].astype(np.float32) @ qe
            ranked = cand[np.argsort(-sc)][:100]
            m = query_metrics(first_ranks(ranked, units[q["need_id"]], doc_hash, doc_law), units[q["need_id"]])
            per.append({"lang": q["lang"], "need_id": q["need_id"], **{k: m[k] for k in ("success@1", "success@5", "success@10", "mrr@10", "ndcg@10")}})
        df = pd.DataFrame(per)
        results[name] = {"seconds_docs": round(t_docs), "params_note": "fp16, 384 tokens", "per_need": per,
                         "summary": {lang: {k: round(float(g[k].mean()), 3) for k in ("success@1", "success@5", "success@10", "mrr@10", "ndcg@10")} for lang, g in df.groupby("lang")}}
        print(name, json.dumps(results[name]["summary"]), f"| docs {t_docs / 60:.1f} min", flush=True)
        out_path.write_text(json.dumps(results, ensure_ascii=False), encoding="utf-8")
        del model, emb
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
