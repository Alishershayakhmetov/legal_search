"""bge-m3 embeddings of all act titles (ru and kk) for the app's title search; resumable shards."""
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "data" / "app"
SHARD = 50_000


def main():
    con = sqlite3.connect(ROOT / "data" / "processed" / "legal.db")
    t = pd.read_sql_query("SELECT law_id, lang, title FROM act_title WHERE is_placeholder = 0 ORDER BY lang, law_id", con)
    con.close()
    t.to_parquet(APP / "titles.parquet", index=False)
    out = APP / "title_emb"
    out.mkdir(exist_ok=True)
    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 96
    texts = t.title.tolist()
    t0 = time.time()
    n = (len(texts) + SHARD - 1) // SHARD
    for s in range(n):
        path = out / f"part_{s:04d}.npy"
        if path.exists():
            continue
        e = model.encode(texts[s * SHARD:(s + 1) * SHARD], batch_size=128, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        tmp = path.with_name(path.stem + ".tmp.npy")
        np.save(tmp, e.astype(np.float16))
        tmp.replace(path)
        print(f"shard {s + 1}/{n}, {(time.time() - t0) / 60:.1f} min", flush=True)
    (out / "DONE").write_text(str(len(texts)))
    print("done", len(texts), flush=True)


if __name__ == "__main__":
    main()
