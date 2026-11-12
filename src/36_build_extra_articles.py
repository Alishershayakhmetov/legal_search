"""Articles the first chunking run missed because their headings have no period ("Статья 1", "1-бап").

The Constitution and many treaties are written that way. The research indexes were built before the chunker accepted such
headings, so the demo app adds them as a supplement: this script chunks only the affected files and writes
data/app/extra_articles.parquet (same columns as articles.parquet); 37_embed_extra.py embeds it.
"""
import hashlib
import importlib.util
import re
import sqlite3
import sys
from multiprocessing import Pool
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chunking import chunk_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
APP = ROOT / "data" / "app"
DOTTED = {"ru": re.compile(r"^Статья\s+\d+(?:-\d+)?\.", re.M), "kk": re.compile(r"^\d+(?:-\d+)?\s*-\s*бап\.", re.M | re.I)}
UNDOTTED = {"ru": re.compile(r"^Статья\s+\d+(?:-\d+)?[ \t]*$", re.M), "kk": re.compile(r"^\d+(?:-\d+)?\s*-\s*бап[ \t]*$", re.M | re.I)}
FOLDERS = {"ru": RAW / "mendeley_ru", "kk": RAW / "mendeley_kk"}

spec = importlib.util.spec_from_file_location("b33", Path(__file__).with_name("33_build_app_data.py"))
b33 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b33)


def process(task):
    lang, path = task
    text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    d, u = len(DOTTED[lang].findall(text)), len(UNDOTTED[lang].findall(text))
    if d >= 3 or d + u < 3:  # already handled by the first run, or no article structure
        return lang, path, []
    passages, _ = chunk_text(text, lang)
    return lang, path, [p for p in passages if p["article_no"] is not None and not p["is_table"]]


def main():
    tasks = [(lang, str(p)) for lang, folder in FOLDERS.items() for p in folder.rglob("*.txt")]
    with Pool(15) as pool:
        results = pool.map(process, tasks, chunksize=64)
    rows = []
    for lang, path, passages in results:
        for i, p in enumerate(passages):
            rows.append({"lang": lang, "rel_path": Path(path).relative_to(RAW).as_posix(), "ord": i, **p})
    extra = pd.DataFrame(rows)
    print(f"files with a supplement: {extra.groupby('lang').rel_path.nunique().to_dict()} | passages: {extra.groupby('lang').size().to_dict()}")

    con = sqlite3.connect(ROOT / "data" / "processed" / "legal.db")
    files = pd.read_sql_query("SELECT file_id, law_id, rel_path FROM text_file", con)
    acts = b33.act_table(con)
    con.close()
    extra = extra.merge(files, on="rel_path", how="left")
    files["file_title"] = files.rel_path.str.rsplit("/", n=1).str[-1].str.rsplit(".", n=1).str[0].str.strip().str[:160]
    extra = extra.merge(acts, on="law_id", how="left").merge(files[["file_id", "file_title"]], on="file_id", how="left")

    base = pd.read_parquet(APP / "articles.parquet")
    base_hashes = {hashlib.md5(t.encode("utf-8")).hexdigest() for t in base.text}
    extra = extra[~extra.text_hash.isin(base_hashes)].drop_duplicates("text_hash")  # keep each text once, as in the base index
    extra["display_title"] = extra.title_ru.where(extra.title_ru.notna(), extra.file_title)
    low = extra.display_title.fillna("").str.lower()
    kk_draft = low.str.contains(r"жоба|жобасы|әзірлеген|ұсынған", regex=True)
    kk_amending = low.str.contains(r"өзгерістер(?: мен толықтырулар)? енгізу|толықтырулар енгізу", regex=True)
    extra["is_draft"] = extra.is_draft.fillna(False).astype(bool) | low.str.startswith(("о проекте", "компиляция")) | kk_draft
    extra["is_amending"] = extra.is_amending.fillna(False).astype(bool) | low.str.startswith(("о внесении изменени", "о внесении дополнени")) | kk_amending
    extra["kind"] = extra.kind.fillna("Другое")
    extra["linked"] = extra.law_id.notna()
    extra["family"] = extra.display_title.fillna("").str.lower().str.replace(r"[«»\"“”„]", "", regex=True).str.strip()
    extra["chunk_id"] = -1
    extra = extra.reset_index(drop=True)
    extra["doc_id"] = 10_000_000 + extra.index
    for col in base.columns:
        if col not in extra.columns:
            extra[col] = None
    extra = extra[list(base.columns)]
    extra.to_parquet(APP / "extra_articles.parquet", index=False, compression="zstd")
    print(f"extra articles written: {len(extra):,} ({extra.linked.mean():.0%} linked, {extra.is_draft.mean():.0%} drafts)")
    const = extra[extra.display_title.str.contains("Конституци", na=False)]
    print("Constitution passages:", const.groupby("lang").size().to_dict(), "| sample:", const[["lang", "article_no"]].head(3).values.tolist())


if __name__ == "__main__":
    main()
