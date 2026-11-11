from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
link = pd.read_parquet(ROOT / "data" / "processed" / "act_text_link.parquet")
for lang in ("ru", "kk"):
    a = link[(link.lang == lang) & (link.match_type == "ambiguous")]
    print(f"\n=== {lang}: ambiguous {len(a)}")
    print("no date parsed in tail:", a.tail_date.isna().sum(), f"({a.tail_date.isna().mean():.0%})")
    print("n_cands quantiles:", a.n_cands.quantile([.5, .75, .9, .99]).to_dict())
    print("best-score distribution:", a.score.describe().round(2).to_dict())
    print("examples without date:")
    for f in a[a.tail_date.isna()].file.sample(4, random_state=2):
        print("   ", Path(f).stem[-130:])
    print("examples with date:")
    for f, d, n in a[a.tail_date.notna()][["file", "tail_date", "n_cands"]].sample(4, random_state=2).itertuples(index=False):
        print("   ", d, n, "|", Path(f).stem[-110:])
