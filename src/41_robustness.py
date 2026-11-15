"""Stage 3: robustness test set (S11) and the "no reliable answer" signal (S13), measured through the app engine.

Perturbed versions of the 45 situation/concept needs per language are made deterministically (seed 7):
  typo_light / typo_heavy  one typo per about 8 / 4 words (swap, delete or double a letter)
  translit                 Latin letters for Russian and Kazakh ("kak vzyskat alimenty")
  nopunct                  lower case, no punctuation
  keywords                 the 4 longest words only
  mixed                    the Russian and the Kazakh question of one need joined in one query (code-switching)
They are searched exactly as the app does (default filters, both languages, language-twin grouping is irrelevant here because
units are matched by text hash). The same run collects the top-1 score and the margin to the 10th result for in-scope
questions and for the off-topic questions of annotation/out_of_scope_queries.json, then reports AUC and the threshold
for the S13 signal. Output: annotation/robustness_queries.jsonl, outputs/robustness.json.
"""
import json
import os
import random
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("QRELS_VERSION", "v1")
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "app"))
from annotation_tools import load_articles  # noqa: E402
from engine import Filters, SearchEngine, detect_language, latin_to_cyrillic  # noqa: E402
from evaluate import build_units, first_ranks, load_queries, query_metrics  # noqa: E402

RU_LAT = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e", "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
          "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
          "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}
KK_LAT = {**RU_LAT, "ә": "a", "ғ": "g", "қ": "k", "ң": "n", "ө": "o", "ұ": "u", "ү": "u", "һ": "h", "і": "i"}
TYPO_OPS = ("swap", "delete", "double")


def typo(text, rate, rng):
    out = []
    for w in text.split():
        core = re.sub(r"\W", "", w)
        if len(core) >= 5 and rng.random() < rate:
            i = rng.randrange(1, len(w) - 2)
            op = rng.choice(TYPO_OPS)
            w = w[:i] + w[i + 1] + w[i] + w[i + 2:] if op == "swap" else (w[:i] + w[i + 1:] if op == "delete" else w[:i] + w[i] + w[i:])
        out.append(w)
    return " ".join(out)


def translit(text, table):
    return "".join(table.get(c.lower(), c) if c.lower() in table else c for c in text)


def keywords(text, n=4):
    words = re.findall(r"\w+", text)
    top = sorted(set(range(len(words))), key=lambda i: -len(words[i]))[:n]
    return " ".join(words[i] for i in sorted(top))


def nopunct(text):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text.lower())).strip()


def make_variants():
    base = load_queries(types={"situation", "concept"})
    rng = random.Random(7)
    by_need = {}
    for q in base:
        by_need.setdefault(q["need_id"], {})[q["lang"]] = q
    rows = []
    for q in base:
        lang, nid, t = q["lang"], q["need_id"], q["text"]
        v = {"clean": t, "typo_light": typo(t, 1 / 8, rng), "typo_heavy": typo(t, 1 / 4, rng), "nopunct": nopunct(t), "keywords": keywords(t)}
        if lang in ("ru", "kk"):
            v["translit"] = translit(t, RU_LAT if lang == "ru" else KK_LAT)
        for name, text in v.items():
            rows.append({"query_id": f"{q['query_id']}:{name}", "need_id": nid, "lang": lang, "variant": name, "text": text})
        if lang == "ru" and "kk" in by_need[nid]:
            rows.append({"query_id": f"{nid}:mixed", "need_id": nid, "lang": "mix", "variant": "mixed", "text": t + " / " + by_need[nid]["kk"]["text"]})
    return rows


def main():
    rows = make_variants()
    with open(ROOT / "annotation" / "robustness_queries.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + chr(10))
    off = json.loads((ROOT / "annotation" / "out_of_scope_queries.json").read_text(encoding="utf-8"))

    engine = SearchEngine()
    _ = engine.model
    mask = engine.mask(Filters())
    doc_ids = engine.df.doc_id.to_numpy()
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "text_hash", "law_id"])
    doc_hash, doc_law = docs.text_hash.to_numpy(), docs.law_id.to_numpy()
    units = build_units(load_articles())

    def search(text, fix=False):
        """Rows and scores as the app's dense search; with fix=True an all-Latin query is also tried as transliterated Russian."""
        rows_, sc = engine._dense_rows(text, mask, 100)
        if fix and detect_language(text) == "en":
            alt = latin_to_cyrillic(text)
            r2, s2 = engine._dense_rows(alt, mask, 100)
            if s2[0] > sc[0]:
                rows_, sc = r2, s2
        return rows_, sc

    results = {}
    for fix in (False, True):
        per = {}
        for r in rows:
            rows_, sc = search(r["text"], fix)
            m = query_metrics(first_ranks(doc_ids[rows_], units[r["need_id"]], doc_hash, doc_law), units[r["need_id"]])
            per.setdefault((r["lang"], r["variant"]), []).append({"need_id": r["need_id"], "s10": m["success@10"], "mrr": m["mrr@10"], "s1": m["success@1"], "top1": float(sc[0]), "margin": float(sc[0] - sc[9])})
        results["fixed" if fix else "plain"] = per
    summary = []
    for mode, per in results.items():
        for (lang, variant), lst in per.items():
            df = pd.DataFrame(lst)
            summary.append({"mode": mode, "lang": lang, "variant": variant, "n": len(df), "s1": round(df.s1.mean(), 3), "s10": round(df.s10.mean(), 3), "mrr": round(df.mrr.mean(), 3)})
    for s in summary:
        if s["mode"] == "plain":
            print(f"{s['lang']:4s} {s['variant']:11s} n={s['n']:3d} S@1 {s['s1']:.2f} S@10 {s['s10']:.2f} MRR {s['mrr']:.3f}")
    print("-- with the transliteration fix")
    for s in summary:
        if s["mode"] == "fixed" and s["variant"] in ("translit", "clean") :
            print(f"{s['lang']:4s} {s['variant']:11s} n={s['n']:3d} S@1 {s['s1']:.2f} S@10 {s['s10']:.2f} MRR {s['mrr']:.3f}")

    # S13: scores of in-scope questions (clean) against off-topic ones
    from sklearn.metrics import roc_auc_score
    signal = {}
    for lang in ("ru", "kk", "en"):
        ins = pd.DataFrame(results["plain"][(lang, "clean")])
        outs = []
        for text in off[lang]:
            _, sc = search(text)
            outs.append({"top1": float(sc[0]), "margin": float(sc[0] - sc[9])})
        outs = pd.DataFrame(outs)
        y = np.r_[np.ones(len(ins)), np.zeros(len(outs))]
        rec = {"n_in": len(ins), "n_out": len(outs)}
        for feat in ("top1", "margin"):
            x = np.r_[ins[feat], outs[feat]]
            rec[f"auc_{feat}"] = round(float(roc_auc_score(y, x)), 3)
        thr = float(np.quantile(ins.top1, 0.05))  # keeps 95% of the in-scope questions
        rec["threshold_top1_keep95"] = round(thr, 3)
        rec["out_rejected"] = int((outs.top1 < thr).sum())
        rec["in_top1_min"], rec["out_top1_max"] = round(float(ins.top1.min()), 3), round(float(outs.top1.max()), 3)
        hard = [float(search(text)[1][0]) for text in off["hard"][lang]]
        rec["hard_top1"] = [round(x, 3) for x in hard]
        rec["hard_rejected"] = int(sum(x < thr for x in hard))
        rec["in_top1_mean"], rec["out_top1_mean"] = round(float(ins.top1.mean()), 3), round(float(outs.top1.mean()), 3)
        signal[lang] = rec
        print(lang, rec)
    out = {"qrels": "v1", "summary": summary, "signal": signal, "out_of_scope_scores": {}}
    (ROOT / "outputs" / "robustness.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
