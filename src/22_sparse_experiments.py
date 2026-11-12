"""Compare analyzers and weighting schemes (keyword overlap, TF-IDF, BM25) on the query set."""
import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402
from evaluate import SUFFIX, build_units, evaluate, load_queries, summarize  # noqa: E402
from search_lib import build_searchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
SCHEMES = ("bm25", "tfidf", "overlap")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scope", choices=["articles", "all"], default="articles")
    ap.add_argument("--modes", default="word,p5,stem")
    ap.add_argument("--langs", default="ru,kk")
    args = ap.parse_args()

    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet")
    if args.scope == "articles":
        docs = docs[docs.is_article].reset_index(drop=True)
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    rows = []
    for lang in args.langs.split(","):
        sub = docs[docs.lang == lang]
        texts, ids = sub.text.tolist(), sub.index.to_numpy()
        qs = [q for q in queries if q["lang"] == lang]
        for mode in args.modes.split(","):
            print(f"[{args.scope}] {lang}/{mode}: {len(texts):,} docs, {len(qs)} queries", flush=True)
            searchers = build_searchers(texts, ids, lang, mode, SCHEMES, log=lambda m: print(m, flush=True))
            for sch, s in searchers.items():
                t0 = time.time()
                per_q = evaluate(lambda text, _l, s=s: s.search(text, 100)[0], qs, units, doc_hash, doc_law)
                ms = (time.time() - t0) / len(qs) * 1000
                summ = summarize(per_q, boot=500)
                rows.append({"scope": args.scope, "lang": lang, "analyzer": mode, "scheme": sch, "n_docs": len(texts),
                             "ms_per_query": round(ms, 1), "index_mb": round(s.size_mb()),
                             **{k: round(v[0], 3) for k, v in summ.items()},
                             "mrr_ci": [round(float(summ["mrr@10"][1]), 3), round(float(summ["mrr@10"][2]), 3)]})
                r = rows[-1]
                print(f"  {sch:8s} S@1 {r['success@1']:.2f} S@5 {r['success@5']:.2f} S@10 {r['success@10']:.2f} R@50 {r['recall@50']:.2f} "
                      f"MRR {r['mrr@10']:.3f} {r['mrr_ci']} nDCG {r['ndcg@10']:.3f} | {ms:.0f} ms/q", flush=True)
            del searchers
    OUT.mkdir(exist_ok=True)
    (OUT / f"sparse_results_{args.scope}_{args.langs.replace(',', '')}_{args.modes.replace(',', '')}{SUFFIX}.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
