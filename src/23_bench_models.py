"""Measure encoding speed, GPU memory and truncation of candidate multilingual embedding models."""
import sys
import time

import numpy as np
import pandas as pd
import torch
from sentence_transformers import SentenceTransformer

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODELS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["intfloat/multilingual-e5-small"]
MAX_LEN = int(sys.argv[2]) if len(sys.argv) > 2 else 256
N = 1536


def main():
    docs = pd.read_parquet(ROOT / "data" / "processed" / "index_docs.parquet", columns=["lang", "text"])
    sample = pd.concat([docs[docs.lang == l].sample(N // 2, random_state=1) for l in ("ru", "kk")]).text.tolist()
    for name in MODELS:
        model = SentenceTransformer(name, device="cuda", model_kwargs={"torch_dtype": torch.float16})
        model.max_seq_length = MAX_LEN
        lens = [len(x) for x in model.tokenizer(sample[:600], add_special_tokens=True)["input_ids"]]
        print(f"\n{name}: params {sum(p.numel() for p in model.parameters()) / 1e6:.0f}M, dim {model.get_sentence_embedding_dimension()}, "
              f"tokens/passage median {int(np.median(lens))} p90 {int(np.percentile(lens, 90))}, truncated at {MAX_LEN}: {np.mean(np.array(lens) > MAX_LEN):.0%}")
        torch.cuda.reset_peak_memory_stats()
        model.encode(["passage: " + t for t in sample[:64]], batch_size=32)  # warm-up
        torch.cuda.synchronize()
        t0 = time.time()
        emb = model.encode(["passage: " + t for t in sample], batch_size=32, normalize_embeddings=True, convert_to_numpy=True)
        torch.cuda.synchronize()
        dt = time.time() - t0
        print(f"  {len(sample) / dt:.0f} passages/s at max_len {MAX_LEN} | peak GPU {torch.cuda.max_memory_allocated() / 1e9:.2f} GB | "
              f"-> 1.70M passages: {1.7e6 / (len(sample) / dt) / 3600:.1f} h")
        del model
        torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
