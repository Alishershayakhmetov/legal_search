"""Select and order the passages that go into the search indexes.

Tables are excluded and exact duplicate texts are kept once per language; the order is by chunk_id so
every index (BM25, dense) shares the same doc_id. The text is stored here once.
"""
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import is_draft_or_compilation  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
OUT = PROC / "index_docs.parquet"
COLUMNS = ["chunk_id", "file_id", "law_id", "lang", "article_no", "is_table", "text_hash", "text"]


def draft_flags():
    con = sqlite3.connect(ROOT / "data" / "processed" / "legal.db")
    rows = con.execute("SELECT law_id, title FROM act_title WHERE lang = 'ru'").fetchall()
    con.close()
    return {lid: is_draft_or_compilation(t) for lid, t in rows}


def main():
    drafts = draft_flags()
    parts = []
    for lang in ("ru", "kk"):
        df = pq.read_table(PROC / f"chunks_{lang}.parquet", columns=COLUMNS).to_pandas()
        n0 = len(df)
        df = df[~df.is_table]
        n1 = len(df)
        # keep the copy that belongs to a real act: linked non-draft first, then draft, then unlinked
        prio = df.law_id.map(lambda x: 2 if x is None else (1 if drafts.get(x, False) else 0))
        df = df.assign(prio=prio).sort_values(["prio", "chunk_id"]).drop_duplicates("text_hash", keep="first")
        print(f"{lang}: {n0:,} passages -> {n1:,} without tables -> {len(df):,} after exact dedup")
        parts.append(df.drop(columns=["is_table", "prio"]))
    docs = pd.concat(parts, ignore_index=True).sort_values("chunk_id", ignore_index=True)
    docs.insert(0, "doc_id", range(len(docs)))
    docs["is_article"] = docs.article_no.notna()
    docs.to_parquet(OUT, index=False, compression="zstd")
    print(f"docs: {len(docs):,} | article passages: {docs.is_article.sum():,} | linked to an act: {docs.law_id.notna().mean():.1%}")
    print("chars:", f"{docs.text.str.len().sum() / 1e9:.2f} G", "| file", f"{OUT.stat().st_size / 1e9:.2f} GB")


if __name__ == "__main__":
    main()
