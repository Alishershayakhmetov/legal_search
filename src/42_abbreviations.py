"""S12: do abbreviations ("ГК", "ТК", "ОСМС") find the right act better when the app spells them out?

Fourteen hand-written questions (annotation/abbreviation_queries.json) each name the expected act by a word in its title; a hit
counts when such a title is among the top 5 results (and, stricter, the first result) of the app's default search. The same engine is run with and without the expansion.
This is a small descriptive check, not a measurement with judgments. Output: outputs/abbreviations.json.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import engine as E  # noqa: E402


def main():
    cases = json.loads((ROOT / "annotation" / "abbreviation_queries.json").read_text(encoding="utf-8"))
    eng = E.SearchEngine()
    _ = eng.model
    real = E.expand_abbreviations
    rows = []
    for name, fn in (("without", lambda q: q), ("with", real)):
        E.expand_abbreviations = fn
        hits_n = top1_n = 0
        for c in cases:
            hits, _ = eng.search(c["q"], 5, "dense")
            ok = any(c["expect"] in h.title.lower() for h in hits)
            hits_n += ok
            top1 = bool(hits) and c["expect"] in hits[0].title.lower()
            top1_n += top1
            rows.append({"mode": name, "query": c["q"], "expect": c["expect"], "found": ok, "found_top1": top1, "top": [f"{h.title[:50]} ст.{h.article_no}" for h in hits[:3]]})
        print(name, "top-5:", hits_n, "top-1:", top1_n, "of", len(cases))
    E.expand_abbreviations = real
    (ROOT / "outputs" / "abbreviations.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    for a, b in zip(rows[:len(cases)], rows[len(cases):]):
        print(f"{a['query'][:45]:45s} top-1 without {a['found_top1']!s:5} with {b['found_top1']!s:5}")


if __name__ == "__main__":
    main()
