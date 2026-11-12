"""Evaluate rankings against the article-level judgments.

A judged article is a unit; a retrieved passage hits the unit when its text hash equals the hash of one of
the unit's passages (so identical text copied into a draft or compilation still counts). Title needs are
judged per act (unit = set of law_ids of the family). A hit on an already-found unit does not take a new
rank: results are collapsed to distinct findings, as a user interface grouping passages by article would.
"""
import hashlib
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "annotation"
CUTOFFS = (1, 5, 10, 20, 50)
QRELS_VERSION = os.environ.get("QRELS_VERSION", "v0")
SUFFIX = "" if QRELS_VERSION == "v0" else f"_{QRELS_VERSION}"


def load_queries(types=None, langs=None):
    rows = [json.loads(line) for line in open(ANN / "queries.jsonl", encoding="utf-8")]
    return [r for r in rows if (types is None or r["type"] in types) and (langs is None or r["lang"] in langs)]


def build_units(articles_df, qrels=None):
    """need_id -> list of {'grade', 'hashes' or 'laws'}."""
    qrels = qrels or json.loads((ANN / f"qrels_{QRELS_VERSION}.json").read_text(encoding="utf-8"))
    by_key = {}
    for r in articles_df.itertuples(index=False):
        by_key.setdefault((r.family, r.article_no), []).append(hashlib.md5(r.text.encode("utf-8")).hexdigest())
    units = {}
    for nid, items in qrels.items():
        us = []
        for j in items:
            if j["article_no"] is None:
                us.append({"grade": j["grade"], "laws": set(j["law_ids"])})
            else:
                hs = set(by_key.get((j["family"], j["article_no"]), []))
                if hs:
                    us.append({"grade": j["grade"], "hashes": hs})
        units[nid] = us
    return units


def first_ranks(ranked, units, doc_hash, doc_law):
    """Collapse the ranking to distinct findings and return (first rank per unit, results list length)."""
    hash_to_units, law_to_units = {}, {}
    for i, u in enumerate(units):
        for h in u.get("hashes", ()):
            hash_to_units.setdefault(h, []).append(i)
        for lw in u.get("laws", ()):
            law_to_units.setdefault(lw, []).append(i)
    found, rank = {}, 0
    for d in ranked:
        hit = set(hash_to_units.get(doc_hash[d], ())) | set(law_to_units.get(doc_law[d], ()))
        new = [i for i in hit if i not in found]
        if hit and not new:
            continue  # only repeats findings already counted
        rank += 1
        for i in new:
            found[i] = rank
    return found


def query_metrics(found, units):
    g2 = [i for i, u in enumerate(units) if u["grade"] == 2]
    ranks2 = [found[i] for i in g2 if i in found]
    m = {f"success@{k}": float(any(r <= k for r in ranks2)) for k in CUTOFFS}
    m.update({f"recall@{k}": (sum(r <= k for r in ranks2) / len(g2)) if g2 else 0.0 for k in CUTOFFS})
    m["mrr@10"] = 1.0 / min(ranks2) if ranks2 and min(ranks2) <= 10 else 0.0
    dcg = sum(units[i]["grade"] / np.log2(r + 1) for i, r in found.items() if r <= 10)
    ideal = sorted((u["grade"] for u in units), reverse=True)[:10]
    idcg = sum(g / np.log2(p + 2) for p, g in enumerate(ideal))
    m["ndcg@10"] = dcg / idcg if idcg else 0.0
    m["judged@10"] = len({r for r in found.values() if r <= 10}) / 10  # share of the top-10 findings that have any judgment
    return m


def evaluate(search_fn, queries, units, doc_hash, doc_law, k=100):
    """search_fn(text, lang) -> ranked global doc ids. Returns per-query metric dicts."""
    out = []
    for q in queries:
        ranked = search_fn(q["text"], q["lang"])[:k]
        found = first_ranks(ranked, units[q["need_id"]], doc_hash, doc_law)
        out.append({"query_id": q["query_id"], "need_id": q["need_id"], "lang": q["lang"], "type": q["type"],
                    **query_metrics(found, units[q["need_id"]])})
    return out


def summarize(rows, keys=("success@1", "success@5", "success@10", "recall@10", "recall@50", "mrr@10", "ndcg@10"), boot=1000, seed=0):
    """Mean of each metric with a 95% bootstrap interval resampling queries."""
    rng = np.random.default_rng(seed)
    res = {}
    for k in keys:
        v = np.array([r[k] for r in rows])
        bs = [v[rng.integers(0, len(v), len(v))].mean() for _ in range(boot)]
        res[k] = (v.mean(), np.percentile(bs, 2.5), np.percentile(bs, 97.5))
    return res
