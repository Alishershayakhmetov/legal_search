"""Embed index documents with a multilingual model, in resumable shards.

usage: 24_embed.py MODEL SCOPE [MAX_LEN]     (SCOPE: articles | all)
Writes data/index/emb_<model>_<scope>/part_XXXX.npy (float16, L2-normalised) and doc_ids.npy.
"""
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

ROOT = Path(__file__).resolve().parent.parent
SHARD = 20_000
PREFIX = {"intfloat/multilingual-e5-small": "passage: ", "intfloat/multilingual-e5-base": "passage: "}


def short(name):
    return name.split("/")[-1]


def main():
    name, scope = sys.argv[1], sys.argv[2]
    max_len = int(sys.argv[3]) if len(sys.argv) > 3 else 384
    out = ROOT / "data" / "index" / f"emb_{short(name)}_{scope}"
    out.mkdir(parents=True, exist_ok=True)
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "is_article", "text"])
    if scope == "articles":
        docs = docs[docs.is_article]
    ids = docs.doc_id.to_numpy()
    fingerprint = hashlib.md5(ids.tobytes()).hexdigest()
    meta_path = out / "meta.json"
    if meta_path.exists() and json.loads(meta_path.read_text())["doc_ids_md5"] != fingerprint:
        raise SystemExit(f"{out} was built from a different document table; delete it or restore index_docs.parquet")
    meta_path.write_text(json.dumps({"model": name, "scope": scope, "max_len": max_len, "n_docs": int(len(ids)),
                                     "shard": SHARD, "doc_ids_md5": fingerprint}))
    np.save(out / "doc_ids.npy", ids)
    texts = docs.text.tolist()
    model = SentenceTransformer(name, device="cuda", model_kwargs={"torch_dtype": torch.float16})
    model.max_seq_length = max_len
    prefix = PREFIX.get(name, "")
    n_shards = (len(texts) + SHARD - 1) // SHARD
    t0 = time.time()
    done_docs = 0
    for s in range(n_shards):
        path = out / f"part_{s:04d}.npy"
        chunk = texts[s * SHARD:(s + 1) * SHARD]
        if path.exists():
            done_docs += len(chunk)
            continue
        emb = model.encode([prefix + t for t in chunk], batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
        tmp = path.with_name(path.stem + ".tmp.npy")
        np.save(tmp, emb.astype(np.float16))
        os.replace(tmp, path)  # a shard either exists complete or not at all, so a stop never leaves a half-written one
        done_docs += len(chunk)
        el = time.time() - t0
        print(f"{short(name)}/{scope}: shard {s + 1}/{n_shards}, {done_docs:,}/{len(texts):,} docs, {el / 60:.1f} min elapsed", flush=True)
    (out / "DONE").write_text(f"{len(texts)} docs, max_len {max_len}\n")
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
