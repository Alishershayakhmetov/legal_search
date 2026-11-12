"""bge-m3 embeddings for data/app/extra_articles.parquet (resumable shards in data/app/extra_emb/)."""
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "data" / "app"
SHARD = 10_000


def main():
    texts = pd.read_parquet(APP / "extra_articles.parquet", columns=["text"]).text.tolist()
    out = APP / "extra_emb"
    out.mkdir(exist_ok=True)
    model = SentenceTransformer("BAAI/bge-m3", device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = 384
    t0 = time.time()
    n = (len(texts) + SHARD - 1) // SHARD
    for s in range(n):
        path = out / f"part_{s:04d}.npy"
        if path.exists():
            continue
        e = model.encode(texts[s * SHARD:(s + 1) * SHARD], batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        tmp = path.with_name(path.stem + ".tmp.npy")
        np.save(tmp, e.astype(np.float16))
        tmp.replace(path)
        print(f"shard {s + 1}/{n}, {(time.time() - t0) / 60:.1f} min", flush=True)
    (out / "DONE").write_text(str(len(texts)))
    print("done", len(texts), flush=True)


if __name__ == "__main__":
    main()
