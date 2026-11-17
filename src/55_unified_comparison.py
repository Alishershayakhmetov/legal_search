"""One table for the course requirement "BM25 vs TF-IDF vs embeddings; Recall@k and MRR on >= 50 annotated queries".

Every method is run on the same 135 article queries (45 situation/concept needs x 3 languages) with judgments v1 and the corpus after the chunker fix
(article index, 319,377 passages), and Recall@1/5/10/20/50, Success@10, MRR@10 and nDCG@10 are recorded per language and pooled. The 24 act-title queries
(8 needs x 3 languages) are evaluated by the title layer (outputs/title_results.json); together that is the 159 queries of the test set.
An appendix lists the earlier result versions (judgments v0, v1 on the old corpus) found in outputs/.
Output: outputs/unified_comparison.json and docs/results_unified.md.
"""
import glob
import importlib.util
import json
import os
import sys
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
KEYS = ("recall@1", "recall@5", "recall@10", "recall@20", "recall@50", "success@10", "mrr@10", "ndcg@10")
LANGS = ("ru", "kk", "en")


def main():
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "lang", "text_hash", "law_id", "is_article", "text"])
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    translated = json.loads((ROOT / "annotation" / "queries_en_translated.json").read_text(encoding="utf-8"))
    art = docs[docs.is_article]
    rows = []

    def record(method, per):
        df = pd.DataFrame(per)
        for lang, g in list(df.groupby("lang")) + [("pooled", df)]:
            rows.append({"method": method, "lang": lang, "n": len(g), **{k: round(float(g[k].mean()), 3) for k in KEYS}})
        print(method, {r["lang"]: r["mrr@10"] for r in rows[-4:] if r["method"] == method}, flush=True)

    def evaluate(method, fn, langs):
        per = []
        for q in queries:
            if q["lang"] not in langs:
                continue
            ranked = np.asarray(fn(q))[:100]
            m = query_metrics(first_ranks(ranked, units[q["need_id"]], doc_hash, doc_law), units[q["need_id"]])
            per.append({"lang": q["lang"], **{k: m[k] for k in KEYS}})
        record(method, per)

    # lexical: three schemes x word forms / best processing
    bm_best = {}
    for lang, modes in (("ru", ("word", "stem")), ("kk", ("word", "p5"))):
        sub = art[art.lang == lang]
        for mode in modes:
            s = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("overlap", "tfidf", "bm25"), log=lambda m: None)
            label = "word forms" if mode == "word" else ("stemming" if mode == "stem" else "5-letter prefix")
            for scheme, name in (("overlap", "Keyword overlap (baseline)"), ("tfidf", "TF-IDF"), ("bm25", "BM25")):
                per = []
                for q in [q for q in queries if q["lang"] == lang]:
                    ranked = s[scheme].search(q["text"], 100)[0]
                    m = query_metrics(first_ranks(np.asarray(ranked)[:100], units[q["need_id"]], doc_hash, doc_law), units[q["need_id"]])
                    per.append({"lang": lang, **{k: m[k] for k in KEYS}})
                key = f"{name}, {label}"
                df = pd.DataFrame(per)
                rows.append({"method": key, "lang": lang, "n": len(df), **{k: round(float(df[k].mean()), 3) for k in KEYS}})
            if (lang, mode) in (("ru", "stem"), ("kk", "p5")):
                bm_best[lang] = s["bm25"]
        print("lexical", lang, "done", flush=True)

    # dense and hybrid
    for model, label in (("intfloat/multilingual-e5-small", "e5-small"), ("intfloat/multilingual-e5-base", "e5-base"), ("BAAI/bge-m3", "bge-m3")):
        dense = de.Dense(model, "articles", docs)
        evaluate(f"Dense {label}", lambda q: dense.search(q["text"], None if q["lang"] == "en" else q["lang"]), LANGS)
        if label == "bge-m3":
            evaluate("Hybrid BM25 + bge-m3 (RRF)", lambda q: de.rrf([bm_best[q["lang"]].search(q["text"], 100)[0], dense.search(q["text"], q["lang"])]), ("ru", "kk"))

            def en_translated(q):
                tr = translated[q["query_id"]]
                return de.rrf([dense.search(tr["ru"], "ru"), dense.search(tr["kk"], "kk")])
            evaluate("English via translation + dense bge-m3", en_translated, ("en",))
            evaluate("English via translation + BM25", lambda q: de.rrf([bm_best["ru"].search(translated[q["query_id"]]["ru"], 100)[0], bm_best["kk"].search(translated[q["query_id"]]["kk"], 100)[0]]), ("en",))
        del dense
        torch.cuda.empty_cache()

    # earlier result versions found in outputs/
    legacy = []
    for p in sorted(glob.glob(str(ROOT / "outputs" / "dense_results_*_articles*.json"))) + sorted(glob.glob(str(ROOT / "outputs" / "sparse_results_articles*.json"))):
        name = Path(p).name
        version = "v1, corpus after chunker fix" if name.endswith("_v1_c2.json") else ("v1, corpus before chunker fix" if name.endswith("_v1_c1.json") else "v0 (102 judgments), corpus before chunker fix")
        for r in json.loads(Path(p).read_text(encoding="utf-8")):
            legacy.append({"file": name, "version": version, "lang": r.get("lang"), "system": r.get("system") or f"{r.get('analyzer')}/{r.get('scheme')}", "model": r.get("model", ""),
                           "success@10": r.get("success@10"), "mrr@10": r.get("mrr@10")})
    out = {"rows": rows, "legacy": legacy, "title": json.loads((ROOT / "outputs" / "title_results.json").read_text(encoding="utf-8"))}
    (ROOT / "outputs" / "unified_comparison.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

    md = ["# Unified comparison: BM25 vs TF-IDF vs embeddings", "",
          "135 article queries (45 needs x ru/kk/en), judgments v1, article index (319,377 passages); plus 24 title queries (8 needs x 3 languages) in the title layer = 159 queries, 53 needs per language.", "",
          "| Method | Lang | n | R@1 | R@5 | R@10 | R@20 | R@50 | S@10 | MRR@10 | nDCG@10 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['method']} | {r['lang']} | {r['n']} | " + " | ".join(f"{r[k]:.3f}" for k in KEYS) + " |")
    p = ROOT / "docs" / "results_unified.md"
    p.write_text(chr(10).join(md) + chr(10), encoding="utf-8")
    print("written", p)


if __name__ == "__main__":
    main()
