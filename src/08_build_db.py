import re
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "data" / "interim" / "laws_metadata.parquet"
LINK = ROOT / "data" / "processed" / "act_text_link.parquet"
SCHEMA = ROOT / "sql" / "schema.sql"
DB = ROOT / "data" / "processed" / "legal.db"

UPPER = "A-ZА-ЯЁӘҒҚҢӨҰҮҺІ0-9"
SPLIT = re.compile(rf"[,;]\s+(?=[{UPPER}])")
PAREN = re.compile(r"\s*\([^()]*\)")
CAPTCHA = "Робот емес"


def split_multi(value):
    """Split a multi-value field on ', ' or '; ' only where the next part starts a new name."""
    parts = [p.strip() for p in SPLIT.split(value.strip()) if p.strip()]
    return list(dict.fromkeys(parts))


def strip_parens(value):
    prev = None
    while prev != value:
        prev, value = value, PAREN.sub("", value)
    return value.strip()


def dim_ids(values):
    return {v: i for i, v in enumerate(sorted(set(values)), start=1)}


def insert_dim(con, table, ids):
    con.executemany(f"INSERT INTO {table} VALUES (?, ?)", [(i, n) for n, i in ids.items()])


def valid_date(series):
    parsed = pd.to_datetime(series, errors="coerce").dt.strftime("%Y-%m-%d")
    return [d if isinstance(d, str) else None for d in parsed]


def main():
    meta = pd.read_parquet(META).fillna("")
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript(SCHEMA.read_text(encoding="utf-8"))

    forms = {lid: split_multi(v) for lid, v in zip(meta.law_id, meta.act_form_ru)}
    areas = {lid: split_multi(v) for lid, v in zip(meta.law_id, meta.legal_relation_area_ru)}
    bodies = {lid: split_multi(strip_parens(v)) for lid, v in zip(meta.law_id, meta.adopting_body_ru)}

    force_ids = dim_ids(meta.legal_force[meta.legal_force != ""])
    region_ids = dim_ids(meta.region_ru[meta.region_ru != ""])
    section_ids = dim_ids(meta.database_section[meta.database_section != ""])
    form_ids = dim_ids(n for v in forms.values() for n in v)
    area_ids = dim_ids(n for v in areas.values() for n in v)
    body_ids = dim_ids(n for v in bodies.values() for n in v)
    for table, ids in [("legal_force", force_ids), ("region", region_ids), ("db_section", section_ids),
                       ("form", form_ids), ("legal_area", area_ids), ("body", body_ids)]:
        insert_dim(con, table, ids)

    adopted = valid_date(meta.date_adopted)
    published = valid_date(meta.date_published)
    print("acts without a valid adoption date:", adopted.count(None), "| without publication date:", published.count(None))
    act_rows = [
        (r.law_id, ad, int(ad[:4]) if ad else None, pub, force_ids.get(r.legal_force),
         region_ids.get(r.region_ru), section_ids.get(r.database_section), int(r.is_repealed == "t"), r.adilet_url)
        for r, ad, pub in zip(meta.itertuples(index=False), adopted, published)
    ]
    con.executemany("INSERT INTO act VALUES (?,?,?,?,?,?,?,?,?)", act_rows)

    title_rows = []
    for r in meta.itertuples(index=False):
        for lang, title in (("ru", r.title_ru), ("kk", r.title_kk)):
            if title.strip():
                title_rows.append((r.law_id, lang, title.strip(), int(CAPTCHA in title)))
    con.executemany("INSERT INTO act_title VALUES (?,?,?,?)", title_rows)

    for table, mapping, ids in [("act_form", forms, form_ids), ("act_area", areas, area_ids), ("act_body", bodies, body_ids)]:
        con.executemany(f"INSERT INTO {table} VALUES (?, ?)",
                        [(lid, ids[n]) for lid, names in mapping.items() for n in names])

    link = pd.read_parquet(LINK)
    link = link.astype(object).where(link.notna(), None)
    con.executemany(
        "INSERT INTO text_file (law_id, lang, rel_path, size_bytes, match_type, n_candidates, match_score) VALUES (?,?,?,?,?,?,?)",
        [(r.law_id, r.lang, r.file, int(r.size), r.match_type, int(r.n_cands), float(r.score)) for r in link.itertuples(index=False)],
    )
    con.commit()

    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    print("foreign key violations:", len(bad))
    for t in ["act", "act_title", "legal_force", "db_section", "region", "form", "legal_area", "body", "act_form", "act_area", "act_body", "text_file"]:
        print(f"{t:12s}", con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0])
    con.execute("ANALYZE")
    con.close()
    print("db size:", f"{DB.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
