"""Show what the best dense system returns for the needs it misses, to judge miss vs incomplete judgments."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402
from evaluate import build_units, first_ranks, load_queries, query_metrics  # noqa: E402
import importlib.util  # noqa: E402

spec = importlib.util.spec_from_file_location("de", Path(__file__).with_name("25_dense_eval.py"))
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)
ROOT = Path(__file__).resolve().parent.parent
NAME, SCOPE = "intfloat/multilingual-e5-base", "articles"

docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "chunk_id", "lang", "text_hash", "law_id", "article_no"])
arts = load_articles()[["chunk_id", "family", "heading"]].drop_duplicates("chunk_id")
docs = docs.merge(arts, on="chunk_id", how="left")
units = build_units(load_articles())
needs = {n["id"]: n for n in __import__("json").load(open(ROOT / "annotation" / "needs.json", encoding="utf-8"))}
dense = de.Dense(NAME, SCOPE, docs)
doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
miss = 0
for q in load_queries(types={"situation", "concept"}, langs={"ru"}):
    ranked = dense.search(q["text"], "ru")[:100]
    found = first_ranks(ranked, units[q["need_id"]], doc_hash, doc_law)
    m = query_metrics(found, units[q["need_id"]])
    if m["success@10"] == 1 or miss >= 7:
        continue
    miss += 1
    gold = [j for j in __import__("json").load(open(ROOT / "annotation" / "qrels_v0.json", encoding="utf-8"))[q["need_id"]] if j["grade"] == 2]
    print(f"\n## {q['need_id']} {q['text'][:90]}\n   gold: " + "; ".join(f"{j['alias']} ст.{j['article_no']} {str(j['heading_ru'])[:40]}" for j in gold))
    for d in ranked[:4]:
        r = docs.iloc[d]
        print(f"   got : {str(r.family)[:34]} ст.{r.article_no} {str(r.heading)[:60]}")
