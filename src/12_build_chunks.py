import argparse
import os
import random
import sqlite3
import time
from collections import Counter
from multiprocessing import Pool
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from chunking import chunk_text

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
DB = ROOT / "data" / "processed" / "legal.db"
OUT_DIR = ROOT / "data" / "processed"
BATCH_ROWS = 50_000

SCHEMA = pa.schema([
    ("chunk_id", pa.int64()), ("file_id", pa.int32()), ("law_id", pa.string()), ("lang", pa.string()),
    ("ord", pa.int32()), ("article_no", pa.string()), ("heading", pa.string()), ("section", pa.string()),
    ("start_char", pa.int32()), ("n_chars", pa.int32()), ("is_table", pa.bool_()), ("text", pa.string()), ("text_hash", pa.string()),
])


def load_tasks(lang):
    con = sqlite3.connect(DB)
    rows = con.execute("SELECT file_id, law_id, rel_path FROM text_file WHERE lang = ? ORDER BY file_id", (lang,)).fetchall()
    con.close()
    return [(fid, lid, lang, rel) for fid, lid, rel in rows]


def process(task):
    file_id, law_id, lang, rel = task
    try:
        text = (RAW / rel).read_text(encoding="utf-8-sig", errors="replace")
    except OSError as e:
        return file_id, law_id, lang, [], {"unreadable": 1, "error": str(e)[:80]}
    passages, stats = chunk_text(text, lang)
    return file_id, law_id, lang, passages, stats


def to_rows(result, counter):
    file_id, law_id, lang, passages, _ = result
    for i, p in enumerate(passages):
        yield (next(counter), file_id, law_id, lang, i, p["article_no"], p["heading"], p["section"],
               p["start_char"], p["n_chars"], p["is_table"], p["text"], p["text_hash"])


def flush(writer, rows):
    if rows:
        writer.write_table(pa.Table.from_pylist([dict(zip(SCHEMA.names, r)) for r in rows], schema=SCHEMA))


def run_lang(lang, out_path, sample, start_id, workers):
    tasks = load_tasks(lang)
    if sample:
        random.Random(11).shuffle(tasks)
        tasks = tasks[:sample]
    print(f"[{lang}] {len(tasks)} files, {workers} workers", flush=True)
    counter = iter(range(start_id, 10**12))
    totals = Counter()
    rows, t0 = [], time.time()
    with pq.ParquetWriter(out_path, SCHEMA, compression="zstd") as writer, Pool(workers) as pool:
        for n, result in enumerate(pool.imap(process, tasks, chunksize=32), start=1):
            stats = result[4]
            totals.update({k: v for k, v in stats.items() if isinstance(v, int)})
            totals["files_with_passages"] += bool(result[3])
            rows.extend(to_rows(result, counter))
            if len(rows) >= BATCH_ROWS:
                totals["passages"] += len(rows)
                flush(writer, rows)
                rows = []
            if n % 10_000 == 0:
                print(f"[{lang}] {n}/{len(tasks)} files, {totals['passages']} passages, {time.time() - t0:.0f}s", flush=True)
        totals["passages"] += len(rows)
        flush(writer, rows)
    print(f"[{lang}] done in {time.time() - t0:.0f}s: {dict(totals)}", flush=True)
    return next(counter), totals


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=0, help="process only N random files per language")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    args = ap.parse_args()
    suffix = "_sample" if args.sample else ""
    next_id = 0
    for lang in ("ru", "kk"):
        next_id, _ = run_lang(lang, OUT_DIR / f"chunks_{lang}{suffix}.parquet", args.sample, next_id, args.workers)


if __name__ == "__main__":
    main()
