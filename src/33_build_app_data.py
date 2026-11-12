"""Compact tables and BM25 indexes for the demo app (data/app/)."""
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import is_draft_or_compilation  # noqa: E402
from search_lib import build_searchers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "data" / "app"
KIND_ORDER = ["Конституционный закон", "Кодекс", "Закон", "Указ", "Постановление", "Распоряжение", "Приказ", "Решение", "Соглашение"]


def act_table(con):
    acts = pd.read_sql_query(
        "SELECT a.law_id, a.adopted_year, a.is_repealed, a.adilet_url, "
        "(SELECT title FROM act_title t WHERE t.law_id = a.law_id AND t.lang = 'ru') AS title_ru, "
        "(SELECT title FROM act_title t WHERE t.law_id = a.law_id AND t.lang = 'kk' AND t.is_placeholder = 0) AS title_kk "
        "FROM act a", con)
    forms = pd.read_sql_query("SELECT af.law_id, f.name FROM act_form af JOIN form f ON f.form_id = af.form_id", con)
    names = forms.groupby("law_id").name.apply(set).to_dict()

    def kind(lid):
        have = names.get(lid, set())
        for k in KIND_ORDER:
            if k in have:
                return k
        return "Другое"

    acts["kind"] = acts.law_id.map(kind)
    low = acts.title_ru.fillna("").str.lower()
    acts["is_draft"] = acts.title_ru.fillna("").map(is_draft_or_compilation)
    acts["is_amending"] = low.str.startswith(("о внесении изменени", "о внесении дополнени"))
    return acts


def main():
    APP.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ROOT / "data" / "processed" / "legal.db")
    acts = act_table(con)
    files = pd.read_sql_query("SELECT file_id, rel_path FROM text_file", con)
    con.close()
    files["file_title"] = files.rel_path.str.rsplit("/", n=1).str[-1].str.rsplit(".", n=1).str[0].str.strip().str[:160]

    ids = np.load(ROOT / "data" / "index" / "emb_bge-m3_articles" / "doc_ids.npy")
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "chunk_id", "file_id", "law_id", "lang", "article_no", "is_article", "text"])
    docs = docs[docs.is_article].sort_values("doc_id").reset_index(drop=True)
    assert np.array_equal(docs.doc_id.to_numpy(), ids), "embedding rows do not match the document table"

    heads = []
    for lang in ("ru", "kk"):
        t = ds.dataset(ROOT / "data" / "processed" / f"chunks_{lang}.parquet").to_table(
            columns=["chunk_id", "heading", "section"], filter=ds.field("article_no").is_valid()).to_pandas()
        heads.append(t)
    heads = pd.concat(heads)
    df = (docs.merge(heads, on="chunk_id", how="left").merge(acts, on="law_id", how="left").merge(files[["file_id", "file_title"]], on="file_id", how="left"))
    df["display_title"] = df.title_ru.where(df.title_ru.notna(), df.file_title)
    low = df.display_title.fillna("").str.lower()
    kk_draft = low.str.contains(r"жоба|жобасы|әзірлеген|ұсынған", regex=True)  # Kazakh titles of bills ("жоба" = draft)
    kk_amending = low.str.contains(r"өзгерістер(?: мен толықтырулар)? енгізу|толықтырулар енгізу", regex=True)
    df["is_draft"] = df.is_draft.fillna(False).astype(bool) | low.str.startswith(("о проекте", "компиляция")) | kk_draft
    df["is_amending"] = df.is_amending.fillna(False).astype(bool) | low.str.startswith(("о внесении изменени", "о внесении дополнени")) | kk_amending
    df["kind"] = df.kind.fillna("Другое")
    df["linked"] = df.law_id.notna()
    df["family"] = df.display_title.fillna("").str.lower().str.replace(r"[«»\"“”„]", "", regex=True).str.strip()
    assert len(df) == len(docs)
    df = df.drop(columns=["file_title", "is_article"])
    df.to_parquet(APP / "articles.parquet", index=False, compression="zstd")
    acts.to_parquet(APP / "acts.parquet", index=False)
    print(f"articles: {len(df):,} | linked {df.linked.mean():.1%} | drafts {df.is_draft.mean():.1%} | amending {df.is_amending.mean():.1%} | in force {(df.is_repealed == 0).mean():.1%}")
    print(df.kind.value_counts().head(8).to_dict())

    extra_path = APP / "extra_articles.parquet"
    if extra_path.exists():  # supplement from 36_build_extra_articles.py: its rows follow the base rows, as in the engine
        df = pd.concat([df, pd.read_parquet(extra_path)], ignore_index=True)
        print(f"BM25 also covers {len(df) - len(docs):,} supplementary articles")
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        sub = df[df.lang == lang]
        s = build_searchers(sub.text.tolist(), sub.index.to_numpy(), lang, mode, ("bm25",), log=lambda m: None)["bm25"]
        s.save(APP / f"bm25_{lang}_{mode}.npz")
        print("bm25", lang, mode, f"{s.size_mb():.0f} MB")


if __name__ == "__main__":
    main()
