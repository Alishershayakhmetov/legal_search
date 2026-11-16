"""D8: a parallel Russian-Kazakh article corpus with an alignment check, built from the corpus the project already has.

Pairs are articles with the same (law_id, article_no) in the Russian and the Kazakh text of one act. Alignment score = cosine of the bge-m3 embeddings
of the first passage of each side (already computed for the search index; bge-m3 is trained on Russian and Kazakh, so the score is cross-lingual) and the
ratio of text lengths. Output: release/parallel/articles_ru_kk.parquet (not published), outputs/parallel_corpus.json (statistics),
outputs/parallel_sample.json (pairs of every score band for a manual read).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "release" / "parallel"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    a = pd.read_parquet(ROOT / "data" / "app" / "articles.parquet", columns=["doc_id", "chunk_id", "lang", "law_id", "article_no", "heading", "text", "title_ru", "title_kk", "adopted_year", "is_draft"])
    ids = np.load(ROOT / "data" / "index" / "emb_bge-m3_articles" / "doc_ids.npy")
    emb = np.concatenate([np.load(p) for p in sorted((ROOT / "data" / "index" / "emb_bge-m3_articles").glob("part_*.npy"))])
    row_of = {d: i for i, d in enumerate(ids)}
    a = a[a.law_id.notna() & ~a.is_draft.astype(bool)].sort_values("chunk_id")
    # one side = the joined passages of one article of one act in one language, plus the row of its first passage
    g = a.groupby(["law_id", "article_no", "lang"], sort=False)
    sides = g.agg(text=("text", lambda s: chr(10).join(s)), first_doc=("doc_id", "first"), heading=("heading", "first"), n_passages=("text", "size"),
                  title_ru=("title_ru", "first"), title_kk=("title_kk", "first"), year=("adopted_year", "first")).reset_index()
    ru, kk = sides[sides.lang == "ru"], sides[sides.lang == "kk"]
    pairs = ru.merge(kk, on=["law_id", "article_no"], suffixes=("_ru", "_kk"))
    pairs["cos"] = [float(emb[row_of[x]].astype(np.float32) @ emb[row_of[y]].astype(np.float32)) for x, y in zip(pairs.first_doc_ru, pairs.first_doc_kk)]
    pairs["len_ratio"] = pairs.text_kk.str.len() / pairs.text_ru.str.len().clip(lower=1)
    pairs["same_passage_count"] = pairs.n_passages_ru == pairs.n_passages_kk
    pairs["tier"] = np.select([pairs.cos >= 0.8, pairs.cos >= 0.7, pairs.cos >= 0.6], ["high", "medium", "low"], "unreliable")
    pairs["aligned"] = (pairs.cos >= 0.7) & pairs.len_ratio.between(0.5, 2.0)
    print("pairs", len(pairs), "acts", pairs.law_id.nunique())
    print(pairs.cos.describe(percentiles=[.01, .05, .1, .25, .5]).round(3).to_dict())
    print(pairs.len_ratio.describe(percentiles=[.05, .5, .95]).round(2).to_dict())

    keep0 = ["law_id", "article_no", "title_ru_ru", "title_kk_kk", "year_ru", "heading_ru", "heading_kk", "text_ru", "text_kk", "n_passages_ru", "n_passages_kk", "cos", "len_ratio"]
    pairs = pairs.rename(columns={"title_ru_ru": "title_ru", "title_kk_kk": "title_kk"})
    keep = ["law_id", "article_no", "title_ru", "title_kk", "year_ru", "heading_ru", "heading_kk", "text_ru", "text_kk", "n_passages_ru", "n_passages_kk", "cos", "len_ratio", "tier", "aligned"]
    pairs[keep].to_parquet(OUT / "articles_ru_kk.parquet", index=False, compression="zstd")
    bands = [(0.0, 0.5), (0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 1.01)]
    stats = {"pairs": int(len(pairs)), "acts": int(pairs.law_id.nunique()), "cos_quantiles": {str(q): round(float(pairs.cos.quantile(q)), 3) for q in (0.01, 0.05, 0.1, 0.25, 0.5, 0.75)},
             "bands": {f"{lo}-{hi}": int(((pairs.cos >= lo) & (pairs.cos < hi)).sum()) for lo, hi in bands},
             "len_ratio_outside_0.5_2": int(((pairs.len_ratio < 0.5) | (pairs.len_ratio > 2)).sum()),
             "aligned": int(pairs.aligned.sum()), "tiers": {k: int(v) for k, v in pairs.tier.value_counts().items()}}
    sample = []
    rng = np.random.default_rng(4)
    for lo, hi in bands:
        sub = pairs[(pairs.cos >= lo) & (pairs.cos < hi)]
        for _, r in sub.sample(min(8, len(sub)), random_state=int(rng.integers(1e6))).iterrows():
            sample.append({"band": f"{lo}-{hi}", "cos": round(r.cos, 3), "len_ratio": round(r.len_ratio, 2), "law_id": r.law_id, "article": r.article_no, "ru": r.text_ru[:350], "kk": r.text_kk[:350]})
    (ROOT / "outputs" / "parallel_corpus.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    (ROOT / "outputs" / "parallel_sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
