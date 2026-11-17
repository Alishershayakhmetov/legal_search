"""Embed index documents with a multilingual model, in resumable shards.

usage: 24_embed.py MODEL SCOPE [MAX_LEN] [REUSE_DIR [OLD_INDEX_DOCS]]     (SCOPE: articles | part | all)

REUSE_DIR is an earlier embedding folder of the same model, scope and max_len; OLD_INDEX_DOCS is the index_docs.parquet it was built from.
Texts whose hash already has a vector there are copied instead of encoded (the vector depends only on the text).
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
PART_FRACTION = 0.15
OLD_DOCS_DEFAULT = ROOT / "data" / "processed" / "v1" / "index_docs.parquet"
PREFIX = {"intfloat/multilingual-e5-small": "passage: ", "intfloat/multilingual-e5-base": "passage: "}


def short(name):
    return name.split("/")[-1]


def load_cache(reuse_dir, old_docs_path, name, scope, max_len):
    """text_hash -> vector of an earlier run, after checking that it is the same model, scope and length."""
    meta = json.loads((reuse_dir / "meta.json").read_text())
    subset_ok = meta["scope"] == "articles" and scope in ("all", "part")  # article vectors are a subset of the larger scopes (same texts, same model)
    if (meta["model"], meta["max_len"]) != (name, max_len) or (meta["scope"] != scope and not subset_ok):
        raise SystemExit(f"{reuse_dir} was built with {meta['model']}/{meta['scope']}/{meta['max_len']}, not {name}/{scope}/{max_len}")
    old_ids = np.load(reuse_dir / "doc_ids.npy")
    parts = [np.load(reuse_dir / f"part_{s:04d}.npy") for s in range((len(old_ids) + meta["shard"] - 1) // meta["shard"])]
    vectors = np.concatenate(parts)
    assert len(vectors) == len(old_ids), "old shards do not match the old doc_ids"
    old = pd.read_parquet(old_docs_path, columns=["doc_id", "text_hash"]).set_index("doc_id").text_hash
    hashes = old.loc[old_ids].to_numpy()
    return {h: i for i, h in enumerate(hashes)}, vectors


def main():
    name, scope = sys.argv[1], sys.argv[2]
    max_len = int(sys.argv[3]) if len(sys.argv) > 3 else 384
    reuse_dir = Path(sys.argv[4]) if len(sys.argv) > 4 else None
    old_docs_path = Path(sys.argv[5]) if len(sys.argv) > 5 else OLD_DOCS_DEFAULT
    out = ROOT / "data" / "index" / f"emb_{short(name)}_{scope}"
    out.mkdir(parents=True, exist_ok=True)
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["doc_id", "is_article", "text", "text_hash"])
    if scope == "articles":
        docs = docs[docs.is_article]
    elif scope == "part":  # all articles plus a fixed random 15% of the other passages (a part of the corpus for a time-limited full-corpus check)
        rest = docs[~docs.is_article].sample(frac=PART_FRACTION, random_state=5)
        docs = docs[docs.is_article | docs.doc_id.isin(rest.doc_id)]
    ids = docs.doc_id.to_numpy()
    fingerprint = hashlib.md5(ids.tobytes()).hexdigest()
    meta_path = out / "meta.json"
    if meta_path.exists() and json.loads(meta_path.read_text())["doc_ids_md5"] != fingerprint:
        raise SystemExit(f"{out} was built from a different document table; delete it or restore index_docs.parquet")
    meta_path.write_text(json.dumps({"model": name, "scope": scope, "max_len": max_len, "n_docs": int(len(ids)),
                                     "shard": SHARD, "doc_ids_md5": fingerprint}))
    np.save(out / "doc_ids.npy", ids)
    texts = docs.text.tolist()
    hashes = docs.text_hash.tolist()
    cache, cached = load_cache(reuse_dir, old_docs_path, name, scope, max_len) if reuse_dir else ({}, None)
    reused = encoded = 0
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
        hs = hashes[s * SHARD:(s + 1) * SHARD]
        todo = [i for i, h in enumerate(hs) if h not in cache]
        shard = np.zeros((len(chunk), model.get_sentence_embedding_dimension()), dtype=np.float16)
        for i, h in enumerate(hs):
            if h in cache:
                shard[i] = cached[cache[h]]
        if todo:
            emb = model.encode([prefix + chunk[i] for i in todo], batch_size=32, normalize_embeddings=True, convert_to_numpy=True, show_progress_bar=False)
            shard[todo] = emb.astype(np.float16)
        reused += len(chunk) - len(todo)
        encoded += len(todo)
        tmp = path.with_name(path.stem + ".tmp.npy")
        np.save(tmp, shard)
        os.replace(tmp, path)  # a shard either exists complete or not at all, so a stop never leaves a half-written one
        done_docs += len(chunk)
        el = time.time() - t0
        print(f"{short(name)}/{scope}: shard {s + 1}/{n_shards}, {done_docs:,}/{len(texts):,} docs ({reused:,} reused, {encoded:,} encoded), {el / 60:.1f} min elapsed", flush=True)
    (out / "DONE").write_text(f"{len(texts)} docs, max_len {max_len}\n")
    print("done", out, flush=True)


if __name__ == "__main__":
    main()
