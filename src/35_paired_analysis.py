"""Per-need comparison of BM25 and bge-m3 (judgments v1) and the needs bge-m3 misses, for the report."""
import importlib.util
import json
import os
import sys
from pathlib import Path

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


def main():
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "chunk_id", "lang", "text_hash", "law_id", "is_article", "article_no", "text"])
    arts = load_articles()[["chunk_id", "family", "heading"]].drop_duplicates("chunk_id")
    meta = docs[["doc_id", "chunk_id"]].merge(arts, on="chunk_id", how="left").set_index("doc_id")
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    dense = de.Dense("BAAI/bge-m3", "articles", docs)
    art_docs = docs[docs.is_article]
    bm25 = {}
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        sub = art_docs[art_docs.lang == lang]
        bm25[lang] = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("bm25",), log=lambda m: None)["bm25"]

    rows = {}
    misses = []
    for q in queries:
        lang, nid = q["lang"], q["need_id"]
        systems = {"dense": dense.search(q["text"], None if lang == "en" else lang)[:100]}
        if lang != "en":
            systems["bm25"] = bm25[lang].search(q["text"], 100)[0]
        for name, ranked in systems.items():
            found = first_ranks(ranked, units[nid], doc_hash, doc_law)
            m = query_metrics(found, units[nid])
            rows.setdefault(nid, {})[f"{lang}_{name}"] = {"s10": m["success@10"], "mrr": m["mrr@10"]}
            if name == "dense" and lang == "ru" and m["success@10"] == 0:
                misses.append({"need": nid, "query": q["text"], "top": [
                    {"family": str(meta.loc[d].family)[:60], "article": str(docs.article_no.iloc[d] if d < len(docs) else ""), "heading": str(meta.loc[d].heading)[:70]}
                    for d in ranked[:3]]})
    pair = {}
    for lang in ("ru", "kk"):
        both = only_d = only_b = neither = 0
        for nid, r in rows.items():
            d, b = r[f"{lang}_dense"]["s10"], r[f"{lang}_bm25"]["s10"]
            both += d == 1 and b == 1
            only_d += d == 1 and b == 0
            only_b += d == 0 and b == 1
            neither += d == 0 and b == 0
        pair[lang] = {"both": int(both), "only_bge_m3": int(only_d), "only_bm25": int(only_b), "neither": int(neither)}
    en_found = sum(r["en_dense"]["s10"] for r in rows.values())
    out = {"paired_success_at_10": pair, "en_found": int(en_found), "n_needs": len(rows), "per_need": rows, "ru_dense_misses": misses}
    (ROOT / "outputs" / "paired_analysis.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(pair, ensure_ascii=False), "| en found:", en_found, "of", len(rows))
    for m in misses:
        print("\n", m["need"], m["query"][:80])
        for t in m["top"]:
            print("    ", t["family"], "ст.", t["article"], t["heading"])


if __name__ == "__main__":
    main()
