"""Read articles for judging: `18_read.py TK:36 TK:37 -n 350` or `18_read.py --find NK "ставка.*10" -n 5`."""
import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import importlib.util  # noqa: E402

from annotation_tools import load_articles  # noqa: E402

spec = importlib.util.spec_from_file_location("find_anchors", Path(__file__).with_name("16_find_anchors.py"))
find_anchors = importlib.util.module_from_spec(spec)
spec.loader.exec_module(find_anchors)
FAMILIES = find_anchors.FAMILIES


def article(df, alias, no, lang="ru"):
    m = df[(df.family == FAMILIES[alias]) & (df.article_no == no) & (df.lang == lang)].sort_values(["law_id", "ord"])
    if m.empty:
        return None, ""
    first_law = m.law_id.iloc[0]
    m = m[m.law_id == first_law]
    return m.heading.iloc[0], "\n".join(m.text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("refs", nargs="*")
    ap.add_argument("--find", nargs=2, metavar=("ALIAS", "REGEX"))
    ap.add_argument("-n", type=int, default=350)
    ap.add_argument("--lang", default="ru")
    a = ap.parse_args()
    df = load_articles()
    if a.find:
        alias, rx = a.find
        sub = df[(df.family == FAMILIES[alias]) & (df.lang == a.lang)]
        hit = sub[sub.text.str.contains(rx, flags=re.I, regex=True)].drop_duplicates("article_no")
        print(f"{len(hit)} articles in {alias} match /{rx}/")
        for r in hit.head(25).itertuples():
            m = re.search(rx, r.text, flags=re.I)
            s = max(m.start() - 60, 0)
            print(f"  ст.{r.article_no:<7} {str(r.heading)[:60]:<60} ...{r.text[s:s + a.n].replace(chr(10), ' ')}")
        return
    for ref in a.refs:
        alias, no = ref.split(":")
        head, text = article(df, alias, no, a.lang)
        print(f"\n=== {ref}  {head}\n{(text or '(not found)')[:a.n]}")


if __name__ == "__main__":
    main()
