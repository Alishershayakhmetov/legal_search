"""Qualitative examples for report v2: top results of BM25 and bge-m3 (same engine, default filters) for a few questions. Read-only."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "app"))
from engine import Filters, SearchEngine  # noqa: E402

CASES = [("ru", "Какое наказание грозит за кражу?"), ("ru", "Сколько длится декретный отпуск и кто его оплачивает?"), ("kk", "Жұмыс беруші менің қызметімді қысқартатынын айтты. Маған қандай төлемдер мен кепілдіктер тиесілі?"),
         ("en", "How long do I have to appeal a court decision?"), ("ru", "Какая ставка НДС в Казахстане?")]
eng = SearchEngine()
_ = eng.model
out = []
for lang, q in CASES:
    row = {"lang": lang, "query": q}
    for method in ("bm25", "dense"):
        if method == "bm25" and lang == "en":
            row[method] = None
            continue
        hits, info = eng.search(q, 3, method, Filters())
        row[method] = [f"{h.title[:70]}, art. {h.article_no}" + (f" — {h.heading[:60]}" if h.heading and h.heading != "None" else "") for h in hits]
    out.append(row)
    print(json.dumps(row, ensure_ascii=False)[:600])
(Path(__file__).parent / "examples.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
