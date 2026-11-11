"""Helpers for building and checking the query test set: article table, family keys, lookups."""
import re
import sqlite3
from pathlib import Path

import pandas as pd
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "legal.db"
CACHE = ROOT / "data" / "interim" / "articles.parquet"

DRAFT_PREFIX = re.compile(r"^\s*(компиляция|о проекте)\s+", re.I)


def family_key(title):
    """Normalise a Russian act title so versions, compilations and drafts of one act share a key."""
    t = DRAFT_PREFIX.sub("", (title or "").lower())
    t = re.sub(r"[«»\"“”„]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def is_draft_or_compilation(title):
    return bool(DRAFT_PREFIX.match((title or "").lower()))


def build_articles():
    parts = []
    for lang in ("ru", "kk"):
        dset = ds.dataset(ROOT / "data" / "processed" / f"chunks_{lang}.parquet")
        t = dset.to_table(
            columns=["chunk_id", "file_id", "law_id", "lang", "ord", "article_no", "heading", "section", "n_chars", "text"],
            filter=ds.field("article_no").is_valid() & ds.field("law_id").is_valid(),
        )
        parts.append(t.to_pandas())
    df = pd.concat(parts, ignore_index=True)
    con = sqlite3.connect(DB)
    acts = pd.read_sql_query(
        "SELECT a.law_id, a.adopted_year, a.is_repealed, t.title AS title_ru "
        "FROM act a JOIN act_title t ON t.law_id = a.law_id AND t.lang = 'ru'", con)
    con.close()
    df = df.merge(acts, on="law_id", how="left")
    df["family"] = df.title_ru.map(family_key)
    df["is_draft"] = df.title_ru.map(is_draft_or_compilation)
    df.to_parquet(CACHE, index=False)
    return df


def load_articles():
    return pd.read_parquet(CACHE) if CACHE.exists() else build_articles()


def article_text(df, family, article_no, lang):
    """All passages of one article in one language (an article can span several passages)."""
    m = df[(df.family == family) & (df.article_no == str(article_no)) & (df.lang == lang)]
    return m.sort_values(["law_id", "ord"])
