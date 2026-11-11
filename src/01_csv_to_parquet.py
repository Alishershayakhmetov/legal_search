import time
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "raw" / "kazakhlawcorpus" / "laws_metadata.csv"
DST = ROOT / "data" / "interim" / "laws_metadata.parquet"

USECOLS = [
    "law_id", "title", "title_kk", "title_ru", "law_registry_number",
    "date_adopted", "date_published",
    "act_form", "act_form_kk", "act_form_ru",
    "legal_relation_area", "legal_relation_area_kk", "legal_relation_area_ru",
    "legal_force", "adopting_body", "adopting_body_kk", "adopting_body_ru",
    "region", "region_kk", "region_ru", "database_section", "is_archive", "is_repealed", "adilet_url",
]
CHUNK = 100_000


def read_chunks():
    return pd.read_csv(SRC, usecols=USECOLS, dtype=str, chunksize=CHUNK, keep_default_na=False)


def main():
    DST.parent.mkdir(parents=True, exist_ok=True)
    writer = None
    rows = 0
    t0 = time.time()
    for i, chunk in enumerate(read_chunks()):
        table = pa.Table.from_pandas(chunk, preserve_index=False)
        if writer is None:
            writer = pq.ParquetWriter(DST, table.schema, compression="zstd")
        writer.write_table(table)
        rows += len(chunk)
        print(f"chunk {i}: {rows} rows, {time.time() - t0:.0f}s", flush=True)
    writer.close()
    print("done", rows, "rows ->", DST, f"{DST.stat().st_size / 1e6:.0f} MB")


if __name__ == "__main__":
    main()
