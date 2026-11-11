"""Pool candidate articles for each need with a crude stemmed TF-IDF over Russian article passages."""
import json
import re
import sys
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WORD = re.compile(r"[^\W\d_]{3,}")
STOP = {"что", "как", "для", "или", "его", "это", "при", "мне", "могу", "если", "какой", "какая", "какие", "ли", "на", "не", "от"}


def stem_tokens(text):
    return [w[:5] for w in WORD.findall(text.lower()) if w not in STOP]


def build_index(df):
    ru = df[(df.lang == "ru") & (~df.is_draft)].reset_index(drop=True)
    vec = TfidfVectorizer(analyzer=stem_tokens, sublinear_tf=True, min_df=2)
    X = vec.fit_transform((ru.heading.fillna("") + " " + ru.heading.fillna("") + " " + ru.text).tolist())
    return ru, vec, X


def pool(ru, vec, X, query, k=8):
    sims = (X @ vec.transform([query]).T).toarray().ravel()
    order = np.argsort(-sims)[:80]
    seen, out = set(), []
    for i in order:
        key = (ru.family[i], ru.article_no[i])
        if key in seen:
            continue
        seen.add(key)
        out.append((float(sims[i]), ru.family[i], ru.article_no[i], ru.heading[i], ru.text[i]))
        if len(out) == k:
            break
    return out


def main():
    df = load_articles()
    ru, vec, X = build_index(df)
    needs = json.loads((ROOT / "annotation" / "needs.json").read_text(encoding="utf-8"))
    only = set(sys.argv[1:])
    for n in needs:
        if n["type"] == "title" or (only and n["id"] not in only):
            continue
        print(f"\n## {n['id']}  {n['ru']}")
        for s, fam, art, head, text in pool(ru, vec, X, n["ru"]):
            print(f"  {s:.2f} [{fam[:38]}] ст.{art} {str(head)[:80]}")


if __name__ == "__main__":
    main()
