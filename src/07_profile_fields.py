from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
df = pd.read_parquet(ROOT / "data" / "interim" / "laws_metadata.parquet").fillna("")
print(df.shape)
for c in ["act_form_ru", "legal_force", "adopting_body_ru", "region_ru", "database_section", "legal_relation_area_ru", "is_archive", "is_repealed"]:
    v = df[c]
    print(f"\n--- {c}: distinct {v.nunique()}, empty {(v == '').mean():.1%}")
    print(v.value_counts().head(6).to_string()[:900])
    for sep in [",", ";", "|", "\n", " / "]:
        print(f"   rows containing {sep!r}: {v.str.contains(sep, regex=False).mean():.1%}")

print("\nlong body example:", df.adopting_body_ru[df.adopting_body_ru.str.len() > 150].iloc[0][:300])
print("area example:", df.legal_relation_area_ru[df.legal_relation_area_ru.str.len() > 150].iloc[0][:500])
for c in ["title_kk", "title_ru", "title"]:
    print(c, "empty", (df[c] == "").mean().round(3), "captcha", df[c].str.contains("Робот емес", regex=False).mean().round(4),
          "short<8", ((df[c].str.len() > 0) & (df[c].str.len() < 8)).mean().round(4))
d = pd.to_datetime(df.date_adopted, errors="coerce")
print("date_adopted parse fail:", d.isna().mean().round(4), "min", d.min(), "max", d.max(), "future>2026-11-03:", (d > "2026-11-03").sum(), "before1991:", (d < "1991-01-01").sum())
print("dup law_id:", df.law_id.duplicated().sum())
