"""D10: a Russian-Kazakh legal term glossary mined from the headings of aligned articles (high-tier pairs of src/48_parallel_corpus.py).

Two parts: (1) whole headings that recur across acts with one dominant Kazakh counterpart ("Заключительные положения" = "Қорытынды ережелер");
(2) single words: Russian stem x Kazakh stem association (Dice over heading pairs) with the commonest surface forms. Output: release/glossary/
glossary_phrases.csv, glossary_words.csv and outputs/glossary_sample.json (random rows for a manual read).
"""
import collections
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from textproc import stem_word  # noqa: E402

OUT = ROOT / "release" / "glossary"
TOKEN = re.compile(r"[^\W\d_]+", re.U)
STOP_RU = {"и", "в", "на", "о", "об", "по", "для", "с", "со", "из", "к", "от", "или", "а", "не", "при", "за", "до"}
STOP_KK = {"және", "мен", "пен", "бен", "туралы", "үшін", "бойынша", "мәселелері", "кезінде", "кезiнде"}


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s-]", " ", s.lower())).strip()


def norm_kk(s):
    """Kazakh heading: Latin look-alikes used in some source texts ('i', 'ı') become the Cyrillic letter 'і'."""
    return norm(s).replace("i", "і").replace("ı", "і")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    p = pd.read_parquet(ROOT / "release" / "parallel" / "articles_ru_kk.parquet", columns=["heading_ru", "heading_kk", "tier", "law_id"])
    p = p[(p.tier == "high") & p.heading_ru.str.len().gt(3) & p.heading_kk.str.len().gt(3)]
    p = p[~p.heading_ru.str.contains("None|nan", regex=True) & ~p.heading_kk.str.contains("None|nan", regex=True)]
    p = p.assign(ru=p.heading_ru.map(norm), kk=p.heading_kk.map(norm_kk))
    print("heading pairs", len(p), "unique ru headings", p.ru.nunique())

    # (1) recurring whole headings
    rows = []
    for ru, grp in p.groupby("ru"):
        n_acts = grp.law_id.nunique()
        if n_acts < 3 or len(ru.split()) > 6:
            continue
        c = collections.Counter(grp.heading_kk.map(norm_kk))
        kk, k = c.most_common(1)[0]
        if k / len(grp) >= 0.6:
            rows.append({"ru": ru, "kk": kk, "acts": int(n_acts), "pairs": len(grp), "consistency": round(k / len(grp), 2)})
    phr = pd.DataFrame(rows).sort_values(["acts", "pairs"], ascending=False)
    phr.to_csv(OUT / "glossary_phrases.csv", index=False, encoding="utf-8")

    # (2) word association over heading pairs
    def stems(text, lang, stop):
        return {stem_word(lang, "p5" if lang == "kk" else "stem", w): w for w in TOKEN.findall(text) if len(w) >= 4 and w not in stop}

    surf_ru, surf_kk = collections.defaultdict(collections.Counter), collections.defaultdict(collections.Counter)
    c_ru, c_kk, c_pair = collections.Counter(), collections.Counter(), collections.Counter()
    for ru, kk in zip(p.ru, p.kk):
        a, b = stems(ru, "ru", STOP_RU), stems(kk, "kk", STOP_KK)
        for s, w in a.items():
            surf_ru[s][w] += 1
        for s, w in b.items():
            surf_kk[s][w] += 1
        c_ru.update(a.keys())
        c_kk.update(b.keys())
        c_pair.update((x, y) for x in a for y in b)
    out = []
    best = {}
    for (x, y), c in c_pair.items():
        if c < 8 or c_ru[x] < 8 or c_kk[y] < 8:
            continue
        dice = 2 * c / (c_ru[x] + c_kk[y])
        if dice >= 0.4 and (x not in best or dice > best[x][0]):
            best[x] = (dice, y, c)
    for x, (dice, y, c) in best.items():
        out.append({"ru": surf_ru[x].most_common(1)[0][0], "kk": surf_kk[y].most_common(1)[0][0], "kk_forms": "; ".join(w for w, _ in surf_kk[y].most_common(3)),
                    "heading_pairs": c, "dice": round(dice, 3)})
    words = pd.DataFrame(out).sort_values(["dice", "heading_pairs"], ascending=False)
    words.to_csv(OUT / "glossary_words.csv", index=False, encoding="utf-8")
    sample = {"phrases": phr.sample(min(40, len(phr)), random_state=2).to_dict("records"), "words": words.sample(min(60, len(words)), random_state=2).to_dict("records")}
    (ROOT / "outputs" / "glossary_sample.json").write_text(json.dumps(sample, ensure_ascii=False, indent=1), encoding="utf-8")
    print("phrases", len(phr), "words", len(words))


if __name__ == "__main__":
    main()
