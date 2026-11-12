"""Title layer: find an act by its name. Compares analyzers, BM25 and dense retrieval on the 'title' needs."""
import json
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402
from evaluate import build_units, first_ranks, load_queries, query_metrics, summarize  # noqa: E402
from search_lib import build_searchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
MODEL = "intfloat/multilingual-e5-small"
RRF_K = 60


def rrf(lists, k=100):
    score = {}
    for lst in lists:
        for r, d in enumerate(lst):
            score[d] = score.get(d, 0.0) + 1.0 / (RRF_K + r + 1)
    return sorted(score, key=score.get, reverse=True)[:k]


def main():
    con = sqlite3.connect(ROOT / "data" / "processed" / "legal.db")
    rows = con.execute("SELECT law_id, lang, title FROM act_title WHERE is_placeholder = 0").fetchall()
    con.close()
    by_lang = {l: [(lid, t) for lid, lg, t in rows if lg == l] for l in ("ru", "kk")}
    units = build_units(load_articles())
    queries = load_queries(types={"title"})
    translated = json.loads((ROOT / "annotation" / "queries_en_translated.json").read_text(encoding="utf-8"))

    model = SentenceTransformer(MODEL, device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 64
    emb, laws, lang_of = [], [], []
    sparse = {}
    for lang in ("ru", "kk"):
        ids, titles = zip(*by_lang[lang])
        e = model.encode(["passage: " + t for t in titles], batch_size=256, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        emb.append(torch.from_numpy(e.astype(np.float16)).to("cuda"))
        laws.append(np.array(ids))
        lang_of.append(np.full(len(ids), lang))
        for mode in ("word", "p5", "stem", "char"):
            s = build_searchers(list(titles), np.arange(len(titles)), lang, mode, ("bm25",), log=lambda m: None)["bm25"]
            sparse[(lang, mode)] = s
        print(lang, len(titles), "titles indexed", flush=True)
    E = dict(zip(("ru", "kk"), emb))
    L = dict(zip(("ru", "kk"), laws))

    def dense(text, lang, k=100):
        q = model.encode(["query: " + text], normalize_embeddings=True, convert_to_tensor=True).half()
        return torch.topk((E[lang] @ q[0]).float(), k).indices.cpu().numpy()

    def run(system, q):
        lang, text = q["lang"], q["text"]
        if lang == "en":
            tr = translated[q["query_id"]]
            if system == "dense_direct":
                return [("ru", dense(text, "ru")), ("kk", dense(text, "kk"))]
            if system == "bm25_translated":
                return [("ru", sparse[("ru", "stem")].search(tr["ru"])[0]), ("kk", sparse[("kk", "p5")].search(tr["kk"])[0])]
            if system == "dense_translated":
                return [("ru", dense(tr["ru"], "ru")), ("kk", dense(tr["kk"], "kk"))]
            if system == "hybrid_translated":
                return [("ru", sparse[("ru", "stem")].search(tr["ru"])[0]), ("kk", sparse[("kk", "p5")].search(tr["kk"])[0]),
                        ("ru", dense(tr["ru"], "ru")), ("kk", dense(tr["kk"], "kk")), ("ru", dense(text, "ru")), ("kk", dense(text, "kk"))]
        if system == "dense":
            return [(lang, dense(text, lang))]
        if system.startswith("bm25_"):
            return [(lang, sparse[(lang, system[5:])].search(text)[0])]
        if system == "hybrid":
            return [(lang, sparse[(lang, "stem" if lang == "ru" else "p5")].search(text)[0]), (lang, dense(text, lang))]

    def to_laws(parts):
        if len(parts) == 1:
            lg, idx = parts[0]
            return L[lg][idx]
        merged = rrf([[(lg, int(i)) for i in idx] for lg, idx in parts])
        return np.array([L[lg][i] for lg, i in merged])

    report = []
    for lang, systems in (("ru", ["bm25_word", "bm25_p5", "bm25_stem", "bm25_char", "dense", "hybrid"]),
                          ("kk", ["bm25_word", "bm25_p5", "bm25_stem", "bm25_char", "dense", "hybrid"]),
                          ("en", ["dense_direct", "bm25_translated", "dense_translated", "hybrid_translated"])):
        qs = [q for q in queries if q["lang"] == lang]
        for system in systems:
            per_q = []
            t0 = time.time()
            for q in qs:
                ranked = to_laws(run(system, q))[:100]
                doc_hash = {l: l for l in set(ranked)}
                found = first_ranks(list(ranked), units[q["need_id"]], doc_hash, doc_hash)
                per_q.append({"query_id": q["query_id"], "need_id": q["need_id"], "lang": lang, "type": "title", **query_metrics(found, units[q["need_id"]])})
            ms = (time.time() - t0) / len(qs) * 1000
            sm = summarize(per_q, boot=300)
            r = {"layer": "title", "lang": lang, "system": system, "n_queries": len(qs), "ms_per_query": round(ms),
                 **{k: round(float(v[0]), 3) for k, v in sm.items()}}
            report.append(r)
            print(f"{lang} {system:18s} S@1 {r['success@1']:.2f} S@5 {r['success@5']:.2f} S@10 {r['success@10']:.2f} MRR {r['mrr@10']:.3f} | {ms:.0f} ms/q", flush=True)
    (ROOT / "outputs" / "title_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
