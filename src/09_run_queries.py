import re
import sqlite3
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "processed" / "legal.db"
QUERIES = ROOT / "sql" / "queries.sql"
OUT = ROOT / "outputs" / "sql"

pd.set_option("display.width", 220)
pd.set_option("display.max_colwidth", 70)


def parse_queries(text):
    blocks = re.split(r"^-- name: (\w+)\s*$", text, flags=re.M)
    return {blocks[i]: blocks[i + 1].strip() for i in range(1, len(blocks), 2)}


def run_all(con, queries):
    results = {}
    for name, sql in queries.items():
        t0 = time.time()
        try:
            df = pd.read_sql_query(sql, con)
        except sqlite3.Error as e:
            print(f"{name}: FAILED {e}")
            continue
        results[name] = df
        print(f"\n### {name}  ({len(df)} rows, {time.time() - t0:.1f}s)")
        print(df.head(12).to_string(index=False))
    return results


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    queries = parse_queries(QUERIES.read_text(encoding="utf-8"))
    print(f"{len(queries)} queries")
    for name, df in run_all(con, queries).items():
        df.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8")
    con.close()


if __name__ == "__main__":
    main()
