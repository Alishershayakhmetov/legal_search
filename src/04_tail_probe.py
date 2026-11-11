import random
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "data" / "interim" / "laws_metadata.parquet"
RU = ROOT / "data" / "raw" / "mendeley_ru"

random.seed(1)
meta = pd.read_parquet(META)
print(meta[["date_adopted", "act_form_ru", "adopting_body_ru", "region", "database_section"]].sample(5, random_state=1).to_string())
print("date_adopted nulls:", (meta["date_adopted"] == "").mean().round(3))

stems = [p.stem for p in RU.rglob("*.txt")]
for s in random.sample(stems, 14):
    print(repr(s))

dup = meta[meta["title_ru"].str.len() > 0].groupby("title_ru").size().sort_values(ascending=False)
print("\ntitles shared by >1 act:", (dup > 1).sum(), "| acts in those:", dup[dup > 1].sum())
top = dup.index[3]
print("example group:", top[:80])
print(meta[meta["title_ru"] == top][["date_adopted", "act_form_ru", "adopting_body_ru", "region", "is_repealed"]].head(6).to_string())
