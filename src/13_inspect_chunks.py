import random
import sqlite3
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from chunking import MIN_ALPHA_RATIO, MIN_LETTERS, LETTER, clean, pack, segments  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
pd.set_option("display.width", 200)

for lang in ("ru", "kk"):
    df = pd.read_parquet(ROOT / "data" / "processed" / f"chunks_{lang}_sample.parquet")
    n = df.n_chars
    print(f"\n=== {lang}: {len(df)} passages from {df.file_id.nunique()} files")
    print("chars: mean", int(n.mean()), "median", int(n.median()), "p5", int(n.quantile(.05)), "p95", int(n.quantile(.95)), "max", int(n.max()))
    print("share < 200 chars:", round((n < 200).mean(), 3), "| > 1500:", round((n > 1500).mean(), 3))
    print("article passages:", int(df.article_no.notna().sum()), "| exact duplicate texts:", round(df.text_hash.duplicated().mean(), 3))
    per_file = df.groupby("file_id").size()
    print("passages per file: median", int(per_file.median()), "p99", int(per_file.quantile(.99)), "max", int(per_file.max()))

# why are kk passages dropped? re-chunk a few files and show dropped pieces
con = sqlite3.connect(ROOT / "data" / "processed" / "legal.db")
rows = con.execute("SELECT rel_path FROM text_file WHERE lang='kk'").fetchall()
random.Random(3).shuffle(rows)
shown = 0
for (rel,) in rows[:400]:
    text = clean((ROOT / "data" / "raw" / rel).read_text(encoding="utf-8-sig", errors="replace"))
    for _, _, _, body in segments(text, "kk"):
        for piece in pack(body):
            letters = len(LETTER.findall(piece))
            if letters < MIN_LETTERS or letters / len(piece) < MIN_ALPHA_RATIO:
                if shown < 8:
                    print(f"\nDROPPED letters={letters} len={len(piece)} ratio={letters / len(piece):.2f}: {piece[:160]!r}")
                shown += 1
print("\ndropped pieces in 400 kk files:", shown)

# show a few kept passages
df = pd.read_parquet(ROOT / "data" / "processed" / "chunks_ru_sample.parquet")
art = df[df.article_no.notna()].sample(2, random_state=1)
for r in art.itertuples():
    print(f"\n[article {r.article_no} | {r.heading} | {r.section}] {r.n_chars} chars\n{r.text[:420]}")
plain = df[df.article_no.isna()].sample(2, random_state=1)
for r in plain.itertuples():
    print(f"\n[plain ord={r.ord}] {r.n_chars} chars\n{r.text[:300]}")
