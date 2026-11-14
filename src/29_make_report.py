"""Assemble docs/results_retrieval_v0.md from the JSON files written by the experiment scripts."""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"


def load(pattern, version="v1"):
    """Result rows of one judgment version; v1 files carry the suffix _v1_c2 (corpus after the chunker fix), v0 files do not."""
    rows = []
    for p in sorted(glob.glob(str(OUT / pattern))):
        if p.endswith("_v1_c2.json") == (version == "v1"):
            rows += json.loads(Path(p).read_text(encoding="utf-8"))
    return rows


def table(header, body):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "---|" * len(header)] + ["| " + " | ".join(map(str, r)) + " |" for r in body])


def metrics(r):
    return [f"{r['success@5']:.2f}", f"{r['success@10']:.2f}", f"{r['recall@50']:.2f}", f"{r['mrr@10']:.3f}", f"{r['ndcg@10']:.3f}"]


MET_HEAD = ["Success@5", "Success@10", "Recall@50", "MRR@10", "nDCG@10"]


def main():
    sparse_art = load("sparse_results_articles*.json")
    sparse_all = load("sparse_results_all_*.json")
    dense = load("dense_results_*.json")
    title = load("title_results.json")
    parts = ["# Retrieval results (judgments v1)", "",
             "Provisional: the judgments are an AI-drafted set that the author has not yet reviewed. Round 1 (hand-checked "
             "articles) was extended in round 2 by judging the top results of eight system runs: 376 articles are judged in total "
             "(67 answer a need, 100 are related, 209 were read and rejected). Judgments are still incomplete, so every number is a "
             "lower bound. 45 non-title needs per language; 95% bootstrap intervals on MRR@10 are wide (about ±0.1), "
             "so differences of a few points are noise.", ""]

    parts += ["## 1. Analyzers and weighting, article passages only (BM25 vs TF-IDF vs keyword overlap)", ""]
    body = [[r["lang"], r["analyzer"], r["scheme"], *metrics(r)] for r in sparse_art]
    parts += [table(["lang", "analyzer", "scheme", *MET_HEAD], body), "",
              "word = word forms, p5 = first five characters, stem = Snowball (ru) or suffix stripping (kk).", ""]

    parts += ["## 2. Systems compared on article passages (230,545 passages, ru and kk)", ""]
    body = []
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        r = next(x for x in sparse_art if x["lang"] == lang and x["analyzer"] == mode and x["scheme"] == "bm25")
        body.append([lang, f"BM25 ({mode})", *metrics(r)])
        for d in dense:
            if d["scope"] == "articles" and d["lang"] == lang and d["system"] in ("dense", "hybrid"):
                body.append([lang, f"{d['model']} {d['system']}", *metrics(d)])
    parts += [table(["lang", "system", *MET_HEAD], body), ""]

    parts += ["## 3. Effect of the corpus: article passages vs all prose passages (BM25)", ""]
    body = []
    for r in sparse_all:
        if r["scheme"] == "bm25":
            a = next(x for x in sparse_art if x["lang"] == r["lang"] and x["analyzer"] == r["analyzer"] and x["scheme"] == "bm25")
            body.append([r["lang"], r["analyzer"], f"{a['n_docs']:,}", f"{a['success@10']:.2f}", f"{a['mrr@10']:.3f}",
                         f"{r['n_docs']:,}", f"{r['success@10']:.2f}", f"{r['mrr@10']:.3f}"])
    parts += [table(["lang", "analyzer", "docs (articles)", "S@10", "MRR", "docs (all prose)", "S@10", "MRR"], body), ""]
    dense_scope = []
    for lang in ("ru", "kk"):
        a = next((d for d in dense if d["model"] == "multilingual-e5-small" and d["scope"] == "articles" and d["lang"] == lang and d["system"] == "dense"), None)
        f = next((d for d in dense if d["model"] == "multilingual-e5-small" and d["scope"] == "all" and d["lang"] == lang and d["system"] == "dense"), None)
        if a and f:
            dense_scope.append([lang, "multilingual-e5-small dense", f"{a['success@10']:.2f}", f"{a['mrr@10']:.3f}", f"{f['success@10']:.2f}", f"{f['mrr@10']:.3f}"])
    if dense_scope:
        parts += ["Same comparison for dense retrieval (e5-small, 230,545 article passages vs 1,699,070 prose passages):", "",
                  table(["lang", "system", "S@10 (articles)", "MRR (articles)", "S@10 (all prose)", "MRR (all prose)"], dense_scope), "",
                  "Every system loses quality when non-article prose (orders, regional decisions) is added; the ranking of the "
                  "systems stays the same. Part of the loss is incomplete judgments: some of those passages may be relevant.", ""]

    parts += ["## 4. English queries (no English text exists in the corpus)", "",
              "direct = the English query against Russian and Kazakh passages with a multilingual model; "
              "translated = NLLB-600M translation of the query into Russian and Kazakh first.", ""]
    body = [[d["model"], d["system"], *metrics(d)] for d in dense if d["lang"] == "en" and d["scope"] == "articles"]
    parts += [table(["model", "system", *MET_HEAD], body), ""]

    parts += ["## 5. Title layer (find an act by name), 8 needs per language, 439,124 titles", "",
              "Eight queries per language: one query is 0.125, so these rows only indicate a direction.", ""]
    body = [[t["lang"], t["system"], f"{t['success@1']:.2f}", f"{t['success@5']:.2f}", f"{t['success@10']:.2f}", f"{t['mrr@10']:.3f}"] for t in title]
    parts += [table(["lang", "system", "Success@1", "Success@5", "Success@10", "MRR@10"], body), ""]

    v0_dense, v0_sparse = load("dense_results_*.json", "v0"), load("sparse_results_articles*.json", "v0")
    cmp_rows = []
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        a0 = next((x for x in v0_sparse if x["lang"] == lang and x["analyzer"] == mode and x["scheme"] == "bm25"), None)
        a1 = next(x for x in sparse_art if x["lang"] == lang and x["analyzer"] == mode and x["scheme"] == "bm25")
        if a0:
            cmp_rows.append([lang, f"BM25 ({mode})", f"{a0['success@10']:.2f}", f"{a1['success@10']:.2f}", f"{a0['mrr@10']:.3f}", f"{a1['mrr@10']:.3f}"])
        for model in ("multilingual-e5-small", "multilingual-e5-base", "bge-m3"):
            d0 = next((x for x in v0_dense if x["model"] == model and x["scope"] == "articles" and x["lang"] == lang and x["system"] == "dense"), None)
            d1 = next((x for x in dense if x["model"] == model and x["scope"] == "articles" and x["lang"] == lang and x["system"] == "dense"), None)
            if d0 and d1:
                cmp_rows.append([lang, f"{model} dense", f"{d0['success@10']:.2f}", f"{d1['success@10']:.2f}", f"{d0['mrr@10']:.3f}", f"{d1['mrr@10']:.3f}"])
    parts += ["## 6. What the second round of judgments changed (article passages)", "",
              table(["lang", "system", "S@10 v0", "S@10 v1", "MRR v0", "MRR v1"], cmp_rows), "",
              "Adding judgments raises every system a little and keeps the order of systems, so the first set was incomplete but "
              "not misleading. The pool came from the same systems that are being compared (and from BM25), which favours them "
              "slightly against a method that was not in the pool.", ""]

    parts += ["## 7. Cost of the dense models (RTX 3050 Laptop 4 GB, fp16, 384 tokens)", "",
              table(["model", "params", "dim", "passages/s", "hours for 1.70M passages", "GPU memory"],
                    [["multilingual-e5-small", "118M", 384, 377, 1.3, "0.4 GB"],
                     ["multilingual-e5-base", "278M", 768, 161, 2.9, "0.8 GB"],
                     ["bge-m3", "568M", 1024, 53, 8.9, "1.5 GB"]]), "",
              "Median passage length is 289 tokens; 8% exceed 384 and are truncated.", ""]
    (ROOT / "docs" / "results_retrieval.md").write_text("\n".join(parts), encoding="utf-8")
    print("wrote docs/results_retrieval.md")


if __name__ == "__main__":
    main()
