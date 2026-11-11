import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "data" / "interim" / "laws_metadata.parquet"
DIRS = {"ru": ROOT / "data" / "raw" / "mendeley_ru", "kk": ROOT / "data" / "raw" / "mendeley_kk"}
TITLE_COL = {"ru": "title_ru", "kk": "title_kk"}
KEYLEN = 5


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower())).strip()


def key(s):
    return " ".join(s.split()[:KEYLEN])


def build_index(titles):
    idx = defaultdict(list)
    for i, t in enumerate(titles):
        n = norm(t)
        if n:
            idx[key(n)].append((n, i))
    return idx


def best_prefix(stem, idx):
    n = norm(stem)
    pool = idx.get(key(n), [])
    cands = [c for c in pool if n.startswith(c[0])]
    if not cands:
        cands = [c for c in pool if c[0].startswith(n)]
    if not cands:
        return None
    longest = max(len(c[0]) for c in cands)
    best = [c for c in cands if len(c[0]) == longest]
    return best[0] + (len(best),)


def main():
    meta = pd.read_parquet(META, columns=["law_id", "title_ru", "title_kk", "act_form_ru", "is_repealed", "date_adopted"])
    print("repealed share:", meta["is_repealed"].value_counts(normalize=True).round(3).to_dict())
    for lang, base in DIRS.items():
        titles = meta[TITLE_COL[lang]].tolist()
        idx = build_index(titles)
        stems = [p.stem for p in base.rglob("*.txt")]
        lens = pd.Series([len(s) for s in stems])
        print(f"\n=== {lang}: {len(stems)} files; stem length median {lens.median():.0f}, p95 {lens.quantile(.95):.0f}, max {lens.max()}, >=250: {(lens >= 250).mean():.1%}")
        hit, matched_ids, ambiguous = 0, set(), 0
        misses = []
        for s in stems:
            m = best_prefix(s, idx)
            if m:
                hit += 1
                matched_ids.add(m[1])
                ambiguous += m[2] > 1
            elif len(misses) < 6:
                misses.append(s)
        print(f"prefix-matched files: {hit}/{len(stems)} = {hit / len(stems):.1%}; distinct acts hit: {len(matched_ids)}; "
              f"files with several equally good candidates (same title): {ambiguous} ({ambiguous / len(stems):.1%})")
        for s in stems[:3]:
            m = best_prefix(s, idx)
            print("  FILE:", s[:230].replace("\n", " "))
            print("  TITLE:", (titles[m[1]][:160] if m else None))
        print("  sample misses:", [x[:120] for x in misses])


if __name__ == "__main__":
    main()
