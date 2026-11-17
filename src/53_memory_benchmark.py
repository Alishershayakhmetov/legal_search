"""Memory and time of the ways to load the 952 MB metadata CSV (and of the search indexes), each measured in a fresh process.

Variants: A) whole CSV, default types; B) whole CSV, the 24 needed columns as strings; C) chunked read (100k rows) written to Parquet, as in
src/01_csv_to_parquet.py; D) the Parquet file read back; E) Parquet plus dtype optimisation (categories for low-cardinality text columns,
datetimes). "Peak" is the peak working set of the process (psutil peak_wset, Windows), "frame" is DataFrame.memory_usage(deep=True).
Output: outputs/memory_benchmark.json. Usage: python src/53_memory_benchmark.py [--worker VARIANT]
"""
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "kazakhlawcorpus" / "laws_metadata.csv"
PQ = ROOT / "data" / "interim" / "laws_metadata.parquet"
USECOLS = ["law_id", "title", "title_kk", "title_ru", "law_registry_number", "date_adopted", "date_published", "act_form", "act_form_kk", "act_form_ru",
           "legal_relation_area", "legal_relation_area_kk", "legal_relation_area_ru", "legal_force", "adopting_body", "adopting_body_kk", "adopting_body_ru",
           "region", "region_kk", "region_ru", "database_section", "is_archive", "is_repealed", "adilet_url"]


def worker(variant):
    import pandas as pd
    import psutil
    t0 = time.time()
    frame = None
    if variant == "A_csv_default":
        frame = pd.read_csv(SRC, low_memory=False)
    elif variant == "B_csv_usecols_str":
        frame = pd.read_csv(SRC, usecols=USECOLS, dtype=str, keep_default_na=False)
    elif variant == "C_chunked_to_parquet":
        import pyarrow as pa
        import pyarrow.parquet as pq
        out = ROOT / "data" / "interim" / "laws_metadata_bench.parquet"
        writer = None
        for chunk in pd.read_csv(SRC, usecols=USECOLS, dtype=str, chunksize=100_000, keep_default_na=False):
            table = pa.Table.from_pandas(chunk, preserve_index=False)
            writer = writer or pq.ParquetWriter(out, table.schema, compression="zstd")
            writer.write_table(table)
        writer.close()
        out.unlink()
    elif variant == "D_parquet":
        frame = pd.read_parquet(PQ)
    elif variant == "E_parquet_optimised":
        frame = pd.read_parquet(PQ)
        for c in ("act_form", "act_form_kk", "act_form_ru", "legal_force", "adopting_body", "adopting_body_kk", "adopting_body_ru", "region", "region_kk", "region_ru",
                  "database_section", "is_archive", "is_repealed"):
            frame[c] = frame[c].astype("category")
        for c in ("date_adopted", "date_published"):
            frame[c] = pd.to_datetime(frame[c], errors="coerce")
    seconds = time.time() - t0
    proc = psutil.Process()
    print(json.dumps({"variant": variant, "seconds": round(seconds, 1), "peak_mb": round(proc.memory_info().peak_wset / 1e6),
                      "frame_mb": None if frame is None else round(float(frame.memory_usage(deep=True).sum()) / 1e6), "rows": None if frame is None else len(frame),
                      "columns": None if frame is None else frame.shape[1]}))


def engine_worker():
    """RAM and GPU memory of the running application: after loading, and after 20 searches."""
    import psutil
    import torch
    sys.path.insert(0, str(ROOT / "app"))
    from engine import Filters, SearchEngine
    proc = psutil.Process()
    t0 = time.time()
    eng = SearchEngine()
    _ = eng.model
    load = {"seconds": round(time.time() - t0, 1), "rss_mb": round(proc.memory_info().rss / 1e6), "gpu_allocated_mb": round(torch.cuda.memory_allocated() / 1e6)}
    for q in ["Сколько дней отпуска положено?", "Какое наказание за кражу?", "Жалдау шартын қалай бұзады?", "How long do I have to appeal a court decision?"] * 5:
        eng.search(q, 8, "dense", Filters())
    print(json.dumps({"after_load": load, "after_20_searches": {"rss_mb": round(proc.memory_info().rss / 1e6), "peak_rss_mb": round(proc.memory_info().peak_wset / 1e6),
                                                                "gpu_allocated_mb": round(torch.cuda.memory_allocated() / 1e6), "gpu_peak_mb": round(torch.cuda.max_memory_allocated() / 1e6)},
                      "articles": len(eng.df)}))


def main():
    if len(sys.argv) > 2 and sys.argv[1] == "--worker":
        return worker(sys.argv[2])
    if len(sys.argv) > 1 and sys.argv[1] == "--engine":
        return engine_worker()
    results = []
    for v in ("A_csv_default", "B_csv_usecols_str", "C_chunked_to_parquet", "D_parquet", "E_parquet_optimised"):
        out = subprocess.run([sys.executable, "-X", "utf8", __file__, "--worker", v], capture_output=True, text=True)
        line = [x for x in out.stdout.splitlines() if x.startswith("{")]
        results.append(json.loads(line[-1]) if line else {"variant": v, "error": out.stderr[-300:]})
        print(results[-1], flush=True)
    eng = subprocess.run([sys.executable, "-X", "utf8", __file__, "--engine"], capture_output=True, text=True)
    line = [x for x in eng.stdout.splitlines() if x.startswith("{")]
    engine = json.loads(line[-1]) if line else {"error": eng.stderr[-300:]}
    print(engine, flush=True)
    sizes = {"csv_mb": round(SRC.stat().st_size / 1e6), "parquet_mb": round(PQ.stat().st_size / 1e6)}
    (ROOT / "outputs" / "memory_benchmark.json").write_text(json.dumps({"files": sizes, "loading": results, "application": engine}, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
