"""Stage 2 ranking experiments on the bge-m3 article index (judgments v1, corpus c2).

Every variant has settings fixed in advance (no tuning on the 45 needs); each is compared with plain bge-m3 on the same
needs (paired bootstrap and exact sign test). Variants:
  base            plain bge-m3 dense search (the reference)
  instr_en/ru     a query instruction in front of the question (S26)
  filters         the demo's default filters: no repealed acts, drafts or amending acts (S3)
  force_*         additive prior by legal force of the act kind (S22), two a-priori weights
  rr / rr_title   bge-reranker-v2-m3 over the top 30, with and without the act title in the passage (S2)
  filters+rr_title  both
  filters+force_*   filters plus the legal-force prior (0.01 / 0.03 / 0.1: a sensitivity sweep, not a selection); with the re-ranker as the last variant
Output: outputs/rank_experiments.json (metrics, paired tests, reranker latency).
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

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("sig", Path(__file__).with_name("39_significance.py"))
sig = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sig)
de = sig.de

TOP_RERANK = 30
FORCE = {"Конституция": 5, "Конституционный закон": 4, "Кодекс": 3, "Закон": 2, "Указ": 1}
INSTR = {"instr_en": "Represent this sentence for searching relevant passages: ",
         "instr_ru": "Найди статью закона Республики Казахстан, отвечающую на вопрос: "}


def main():
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "lang", "text_hash", "law_id", "is_article"])
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    app = pd.read_parquet(ROOT / "data" / "app" / "articles.parquet")
    emb_ids = np.load(ROOT / "data" / "index" / "emb_bge-m3_articles" / "doc_ids.npy")
    assert len(app) == len(emb_ids) and np.array_equal(app.doc_id.to_numpy(), emb_ids)
    units = build_units(load_articles())
    queries = load_queries(types={"situation", "concept"})
    needs = {n["id"]: n for n in json.loads((ROOT / "annotation" / "needs.json").read_text(encoding="utf-8"))}

    dense = de.Dense("BAAI/bge-m3", "articles", docs)
    lang_mask = {l: dense.mask[l] for l in ("ru", "kk")}
    keep = torch.from_numpy(((app.is_repealed.fillna(0) == 0) & ~app.is_draft.astype(bool) & ~app.is_amending.astype(bool)).to_numpy()).to("cuda")
    force = torch.from_numpy(app.kind.map(FORCE).fillna(0).to_numpy(dtype=np.float32)).to("cuda")
    texts = app.text.tolist()
    titles = app.display_title.fillna("").tolist()

    from sentence_transformers import CrossEncoder
    rr = CrossEncoder("BAAI/bge-reranker-v2-m3", max_length=512, device="cuda", model_kwargs={"torch_dtype": torch.float16})

    def retrieve(text, lang, prefix="", only_keep=False, prior=0.0, k=100):
        q = dense.model.encode([prefix + text], normalize_embeddings=True, convert_to_tensor=True).half()
        s = (dense.emb @ q[0]).float()
        if lang in lang_mask:
            s = s.masked_fill(~lang_mask[lang], -1e4)
        if only_keep:
            s = s.masked_fill(~keep, -1e4)
        if prior:
            s = s + prior * force
        return torch.topk(s, k).indices.cpu().numpy()

    rerank_seconds = []

    def rerank(text, rows, with_title):
        head = rows[:TOP_RERANK]
        pairs = [(text, (titles[i] + ". " if with_title else "") + texts[i]) for i in head]
        t0 = time.time()
        scores = rr.predict(pairs, batch_size=16, show_progress_bar=False)
        torch.cuda.synchronize()
        rerank_seconds.append(time.time() - t0)
        order = np.argsort(-np.asarray(scores), kind="stable")
        return np.concatenate([head[order], rows[TOP_RERANK:]])

    variants = {
        "base": lambda q: retrieve(q["text"], q["_l"]),
        "instr_en": lambda q: retrieve(q["text"], q["_l"], INSTR["instr_en"]),
        "instr_ru": lambda q: retrieve(q["text"], q["_l"], INSTR["instr_ru"]),
        "filters": lambda q: retrieve(q["text"], q["_l"], only_keep=True),
        "force_0.01": lambda q: retrieve(q["text"], q["_l"], prior=0.01),
        "force_0.03": lambda q: retrieve(q["text"], q["_l"], prior=0.03),
        "rr": lambda q: rerank(q["text"], retrieve(q["text"], q["_l"]), False),
        "rr_title": lambda q: rerank(q["text"], retrieve(q["text"], q["_l"]), True),
        "filters+rr_title": lambda q: rerank(q["text"], retrieve(q["text"], q["_l"], only_keep=True), True),
        "filters+force_0.01": lambda q: retrieve(q["text"], q["_l"], only_keep=True, prior=0.01),
        "filters+force_0.02": lambda q: retrieve(q["text"], q["_l"], only_keep=True, prior=0.02),
        "filters+force_0.03": lambda q: retrieve(q["text"], q["_l"], only_keep=True, prior=0.03),
        "filters+force_0.1": lambda q: retrieve(q["text"], q["_l"], only_keep=True, prior=0.1),
        "filters+force_0.03+rr_title": lambda q: rerank(q["text"], retrieve(q["text"], q["_l"], only_keep=True, prior=0.03), True),
    }
    only = [v for v in os.environ.get("ONLY", "").split(",") if v]
    if only:  # quick re-run of selected variants (the base is always included)
        variants = {k: v for k, v in variants.items() if k == "base" or k in only}
    per = {}
    latency = {}
    for name, fn in variants.items():
        rerank_seconds.clear()
        t_start = time.time()
        for q in queries:
            q = dict(q, _l=None if q["lang"] == "en" else q["lang"])
            rows = fn(q)
            ranked = emb_ids[rows[:100]]
            m = query_metrics(first_ranks(ranked, units[q["need_id"]], doc_hash, doc_law), units[q["need_id"]])
            per.setdefault((q["lang"], name), []).append({"need_id": q["need_id"], **{k: m[k] for k in ("success@1", "success@5", "success@10", "mrr@10", "ndcg@10")}})
        latency[name] = {"total_ms_per_query": round((time.time() - t_start) / len(queries) * 1000), "rerank_ms_per_query": round(float(np.mean(rerank_seconds)) * 1000) if rerank_seconds else 0}
        print(name, latency[name], flush=True)

    rng = np.random.default_rng(0)
    summary, tests = [], []
    for (lang, name), rows in per.items():
        df = pd.DataFrame(rows).sort_values("need_id").reset_index(drop=True)
        summary.append({"lang": lang, "variant": name, **{k: round(float(df[k].mean()), 3) for k in df.columns if k != "need_id"}})
        if name != "base":
            b = pd.DataFrame(per[(lang, "base")]).sort_values("need_id").reset_index(drop=True)
            a_s, b_s = df["success@10"].to_numpy(), b["success@10"].to_numpy()
            d10 = sig.paired(a_s, b_s, rng)
            dm = sig.paired(df["mrr@10"].to_numpy(), b["mrr@10"].to_numpy(), rng)
            a_only, b_only = int(((a_s == 1) & (b_s == 0)).sum()), int(((a_s == 0) & (b_s == 1)).sum())
            tests.append({"lang": lang, "variant": name, "s10_diff": [round(x, 3) for x in d10], "mrr_diff": [round(x, 3) for x in dm],
                          "better": a_only, "worse": b_only, "sign_p": round(sig.sign_test_p(a_only, b_only), 4)})
    out = {"qrels": "v1", "corpus": "c2", "top_rerank": TOP_RERANK, "summary": summary, "tests_vs_base": tests, "latency": latency}
    path = ROOT / "outputs" / "rank_experiments.json"
    if only and path.exists():  # a partial re-run replaces its own variants in the saved result
        old = json.loads(path.read_text(encoding="utf-8"))
        redo = set(only)
        out = {**old, "summary": [r for r in old["summary"] if r["variant"] not in redo] + [r for r in summary if r["variant"] in redo],
               "tests_vs_base": [r for r in old["tests_vs_base"] if r["variant"] not in redo] + [r for r in tests if r["variant"] in redo],
               "latency": {**old["latency"], **{k: v for k, v in latency.items() if k in redo}}}
    path.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for lang in ("ru", "kk", "en"):
        print(f"\n[{lang}]")
        for r in [s for s in summary if s["lang"] == lang]:
            t = next((x for x in tests if x["lang"] == lang and x["variant"] == r["variant"]), None)
            extra = f" | dS@10 {t['s10_diff']} dMRR {t['mrr_diff']} better/worse {t['better']}/{t['worse']} p={t['sign_p']}" if t else ""
            print(f"  {r['variant']:18s} S@1 {r['success@1']:.2f} S@5 {r['success@5']:.2f} S@10 {r['success@10']:.2f} MRR {r['mrr@10']:.3f} nDCG {r['ndcg@10']:.3f}{extra}")


if __name__ == "__main__":
    main()
