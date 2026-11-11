import sqlite3
from pathlib import Path

import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "legal.db"
DDL = ROOT / "sql" / "passage.sql"
COLUMNS = ["chunk_id", "file_id", "ord", "article_no", "heading", "section", "n_chars", "is_table", "text_hash"]


def main():
    con = sqlite3.connect(DB)
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(DDL.read_text(encoding="utf-8"))
    total = 0
    for lang in ("ru", "kk"):
        pf = pq.ParquetFile(ROOT / "data" / "processed" / f"chunks_{lang}.parquet")
        for batch in pf.iter_batches(batch_size=100_000, columns=COLUMNS):
            cols = batch.to_pydict()
            cols["is_table"] = [int(x) for x in cols["is_table"]]
            con.executemany("INSERT INTO passage VALUES (?,?,?,?,?,?,?,?,?)", zip(*(cols[c] for c in COLUMNS)))
            total += batch.num_rows
        con.commit()
        print(lang, "loaded, running total", total, flush=True)
    bad = con.execute("PRAGMA foreign_key_check").fetchall()
    print("foreign key violations:", len(bad))
    con.execute("ANALYZE")
    con.close()
    print("db size:", f"{DB.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
