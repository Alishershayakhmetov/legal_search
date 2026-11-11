import json, sys
from pathlib import Path
pool = json.loads((Path(__file__).resolve().parent.parent / "annotation" / "pool_round2.json").read_text(encoding="utf-8"))
ids = list(pool)
a, b = int(sys.argv[1]), int(sys.argv[2])
for nid in ids[a:b]:
    print(f"\n##### {nid}: {pool[nid]['ru']}")
    for i, c in enumerate(pool[nid]["candidates"]):
        body = c["text"].split("\n", 1)[1] if "\n" in c["text"] else c["text"]
        print(f"[{i}] {c['family'][:36]} ст.{c['article_no']} | {c['heading'][:70]} | v{len(c['voters'])}\n     {body[:210].replace(chr(10), ' ')}")
