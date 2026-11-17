"""bge-m3 on a part of the full corpus: all article passages plus a fixed random 15% of the other passages (530,772 passages, 31% of the index).

The same document subset is used for every system so the comparison is fair: BM25 (Russian stemming, Kazakh 5-letter prefix) is rebuilt on the subset,
e5-small vectors are taken from the all-passage embedding restricted to the subset, bge-m3 vectors come from data/index/emb_bge-m3_part.
Judgments v1, 45 situation/concept needs per language, collapsed findings. Output: outputs/part_corpus_eval.json.
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
KEYS = ("success@1", "success@5", "success@10", "recall@10", "recall@50", "mrr@10", "ndcg@10")


def main():
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "lang", "text_hash", "law_id", "is_article", "text"])
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    part_ids = np.load(ROOT / "data" / "index" / "emb_bge-m3_part" / "doc_ids.npy")
    part = docs.iloc[part_ids]
    print("part:", len(part), "passages;", int(part.is_article.sum()), "articles;", f"{len(part) / len(docs):.1%} of the index", flush=True)

    systems = {}
    bm = {}
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        sub = part[part.lang == lang]
        bm[lang] = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("bm25",), log=lambda m: None)["bm25"]
    systems["BM25"] = lambda q: bm[q["lang"]].search(q["text"], 100)[0] if q["lang"] in bm else np.array([], dtype=np.int64)

    # e5-small restricted to the subset
    e5 = de.Dense("intfloat/multilingual-e5-small", "all", docs)
    keep = torch.from_numpy(np.isin(e5.ids, part_ids)).to("cuda")
    e5.mask = {**{l: m & keep for l, m in e5.mask.items()}, None: keep}  # None: English queries search both languages
    systems["e5-small"] = lambda q: e5.search(q["text"], None if q["lang"] == "en" else q["lang"])
    results = {}

    def run(name, fn, langs=("ru", "kk", "en")):
        per, t0 = [], time.time()
        for q in [q for q in queries if q["lang"] in langs]:
            ranked = np.asarray(fn(q))[:100]
            m = query_metrics(first_ranks(ranked, units[q["need_id"]], doc_hash, doc_law), units[q["need_id"]])
            per.append({"lang": q["lang"], **{k: m[k] for k in KEYS}})
        df = pd.DataFrame(per)
        results[name] = {lang: {k: round(float(g[k].mean()), 3) for k in KEYS} for lang, g in df.groupby("lang")}
        results[name]["ms_per_query"] = round((time.time() - t0) / max(len(per), 1) * 1000)
        print(name, json.dumps(results[name]), flush=True)

    run("BM25", systems["BM25"], langs=("ru", "kk"))
    run("e5-small", systems["e5-small"])
    del e5
    torch.cuda.empty_cache()
    bge = de.Dense("BAAI/bge-m3", "part", docs)
    run("bge-m3", lambda q: bge.search(q["text"], None if q["lang"] == "en" else q["lang"]))
    run("hybrid BM25 + bge-m3", lambda q: de.rrf([bm[q["lang"]].search(q["text"], 100)[0], bge.search(q["text"], q["lang"])]), langs=("ru", "kk"))
    out = {"passages": int(len(part)), "articles": int(part.is_article.sum()), "share_of_index": round(len(part) / len(docs), 3), "systems": results}
    (ROOT / "outputs" / "part_corpus_eval.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
