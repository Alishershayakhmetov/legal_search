"""A10/A11: how much of the amendment history can be read from the notes in the article texts, and does it look right?

Parses every article of data/app/articles.parquet with app/amendments.py, reports coverage, and writes a random sample of parsed
footnotes next to their source lines (outputs/amendments_sample.json) for a manual read. Output: outputs/amendments.json.
"""
import json
import random
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
from amendments import FOOTNOTE, PENDING_MARK, parse_notes  # noqa: E402


def main():
    a = pd.read_parquet(ROOT / "data" / "app" / "articles.parquet", columns=["text", "lang", "display_title", "article_no"])
    stats = Counter()
    pend_status = Counter()
    pool = []
    today = date(2026, 11, 15)
    for row in a.itertuples(index=False):
        lines = row.text.split(chr(10))
        has_fn = any(FOOTNOTE.match(x.strip()) for x in lines)
        has_pn = any(PENDING_MARK.match(x.strip()) for x in lines)
        stats[f"{row.lang}_articles"] += 1
        if not (has_fn or has_pn):
            continue
        r = parse_notes(row.text, row.lang, today)
        stats[f"{row.lang}_with_footnote"] += has_fn
        stats[f"{row.lang}_with_pending_note"] += has_pn
        stats[f"{row.lang}_footnote_parsed"] += has_fn and bool(r["history"])
        stats[f"{row.lang}_pending_parsed"] += has_pn and bool(r["pending"])
        stats["entries"] += len(r["history"])
        stats["entries_with_abs_effective_date"] += sum(1 for h in r["history"] if h["effective_date"])
        for p in r["pending"]:
            pend_status[p["status"]] += 1
        if has_fn or has_pn:
            pool.append((row, r))
    random.Random(5).shuffle(pool)
    sample = [{"lang": row.lang, "title": row.display_title, "article": row.article_no,
               "source": [x.strip()[:700] for x in row.text.split(chr(10)) if FOOTNOTE.match(x.strip()) or PENDING_MARK.match(x.strip())][:3], "parsed": r}
              for row, r in pool[:40]]
    (ROOT / "outputs" / "amendments_sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1), encoding="utf-8")
    out = {"today": today.isoformat(), "stats": dict(stats), "pending_status": dict(pend_status)}
    (ROOT / "outputs" / "amendments.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
