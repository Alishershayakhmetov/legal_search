"""Translate the English queries into Russian and Kazakh with NLLB, for the query-translation strategy."""
import json
from pathlib import Path

import torch
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

ROOT = Path(__file__).resolve().parent.parent
NAME = "facebook/nllb-200-distilled-600M"
TARGETS = {"ru": "rus_Cyrl", "kk": "kaz_Cyrl"}


def main():
    queries = [json.loads(line) for line in open(ROOT / "annotation" / "queries.jsonl", encoding="utf-8")]
    en = [q for q in queries if q["lang"] == "en"]
    tok = AutoTokenizer.from_pretrained(NAME, src_lang="eng_Latn")
    model = AutoModelForSeq2SeqLM.from_pretrained(NAME, torch_dtype=torch.float16).to("cuda").eval()
    out = {q["query_id"]: {} for q in en}
    for lang, code in TARGETS.items():
        for i in range(0, len(en), 16):
            batch = en[i:i + 16]
            enc = tok([q["text"] for q in batch], return_tensors="pt", padding=True).to("cuda")
            with torch.no_grad():
                gen = model.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids(code), num_beams=4, max_new_tokens=96)
            for q, t in zip(batch, tok.batch_decode(gen, skip_special_tokens=True)):
                out[q["query_id"]][lang] = t
    (ROOT / "annotation" / "queries_en_translated.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    for qid in list(out)[:4]:
        print(qid, out[qid])


if __name__ == "__main__":
    main()
