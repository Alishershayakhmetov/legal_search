"""Round-2 pooling: collect the top results of every retrieval system for every non-title need and list the
articles that are not judged yet. Output: annotation/pool_round2.json (read by hand, then judged).
"""
import gc
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402
from evaluate import build_units, load_queries  # noqa: E402
from search_lib import build_searchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "annotation"
DEPTH = 10
PER_NEED = 6
RRF_K = 60

spec = importlib.util.spec_from_file_location("de", Path(__file__).with_name("25_dense_eval.py"))
de = importlib.util.module_from_spec(spec)
spec.loader.exec_module(de)


def article_key_table(docs, arts):
    """doc_id -> (family, article_no, is_draft) for article passages linked to an act."""
    m = docs[["doc_id", "chunk_id"]].merge(arts[["chunk_id", "family", "article_no", "is_draft"]], on="chunk_id", how="left")
    return m.set_index("doc_id")


def main():
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "chunk_id", "lang", "text_hash", "law_id", "is_article", "text"])
    arts = load_articles()
    keys = article_key_table(docs, arts)
    units = build_units(arts)
    needs = {n["id"]: n for n in json.loads((ANN / "needs.json").read_text(encoding="utf-8"))}
    queries = [q for q in load_queries(types={"situation", "concept"}) if q["need_id"] in json.loads((ANN / "qrels_v0.json").read_text(encoding="utf-8"))]
    by_need = {}
    for q in queries:
        by_need.setdefault(q["need_id"], {})[q["lang"]] = q["text"]

    runs = {}  # (system, need) -> ranked list of (family, article_no) in order, collapsed

    def collapse(ranked):
        seen, out = set(), []
        for d in ranked:
            k = keys.loc[d]
            if pd.isna(k.family):
                continue
            key = (k.family, k.article_no)
            if key not in seen:
                seen.add(key)
                out.append(key)
        return out

    art_docs = docs[docs.is_article]
    for model, langs in (("BAAI/bge-m3", ("ru", "kk", "en")), ("intfloat/multilingual-e5-base", ("ru",)), ("intfloat/multilingual-e5-small", ("ru", "kk"))):
        dense = de.Dense(model, "articles", docs)
        for nid, q in by_need.items():
            for lang in langs:
                runs[(f"{model.split('/')[-1]}:{lang}", nid)] = collapse(dense.search(q[lang], None if lang == "en" else lang, k=60))[:DEPTH]
        del dense
        gc.collect()
        torch.cuda.empty_cache()
        print("dense done:", model, flush=True)
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        sub = art_docs[art_docs.lang == lang]
        s = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("bm25",), log=lambda m: None)["bm25"]
        for nid, q in by_need.items():
            runs[(f"bm25:{lang}", nid)] = collapse(s.search(q[lang], 100)[0])[:DEPTH]
        print("bm25 done:", lang, flush=True)

    # an article already judged (any grade) is identified by family + article number
    qrels0 = json.loads((ANN / "qrels_v0.json").read_text(encoding="utf-8"))
    judged = {nid: {(j["family"], j["article_no"]) for j in items} for nid, items in qrels0.items()}
    out = {}
    for nid in by_need:
        score, voters, best = {}, {}, {}
        for (system, n), lst in runs.items():
            if n != nid:
                continue
            for r, key in enumerate(lst):
                score[key] = score.get(key, 0.0) + 1.0 / (RRF_K + r + 1)
                voters.setdefault(key, []).append(f"{system}#{r + 1}")
        cands = [k for k in sorted(score, key=score.get, reverse=True) if k not in judged[nid]]
        rows = []
        for fam, art_no in cands:
            sub = arts[(arts.family == fam) & (arts.article_no == art_no)]
            if sub[~sub.is_draft].empty:
                continue  # drafts and bills are not the law
            sub = sub[~sub.is_draft]
            ru = sub[sub.lang == "ru"].sort_values(["law_id", "ord"])
            text_row = ru if len(ru) else sub[sub.lang == "kk"].sort_values(["law_id", "ord"])
            first = text_row[text_row.law_id == text_row.law_id.iloc[0]]
            rows.append({"family": fam, "article_no": art_no, "heading": str(first.heading.iloc[0]), "text": "\n".join(first.text)[:700],
                         "voters": voters[(fam, art_no)], "score": round(score[(fam, art_no)], 4)})
            if len(rows) == PER_NEED:
                break
        out[nid] = {"ru": needs[nid]["ru"], "candidates": rows}
    (ANN / "pool_round2.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    n_cand = sum(len(v["candidates"]) for v in out.values())
    print(f"needs: {len(out)} | new candidates to judge: {n_cand} (max {PER_NEED} per need)")


if __name__ == "__main__":
    main()
