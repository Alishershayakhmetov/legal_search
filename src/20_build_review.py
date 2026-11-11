"""Generate annotation/review.html: a self-contained page for confirming judgments and fixing queries."""
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "annotation"
SNIPPET = 900

spec = importlib.util.spec_from_file_location("rd", Path(__file__).with_name("18_read.py"))
rd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rd)

TEMPLATE = (ANN / "review_template.html").read_text(encoding="utf-8")


def article_by_family(df, family, article_no, lang):
    m = df[(df.family == family) & (df.article_no == article_no) & (df.lang == lang)].sort_values(["law_id", "ord"])
    if m.empty:
        return None, ""
    m = m[m.law_id == m.law_id.iloc[0]]
    return m.heading.iloc[0], chr(10).join(m.text)


def main():
    df = load_articles()
    needs = {n["id"]: n for n in json.loads((ANN / "needs.json").read_text(encoding="utf-8"))}
    qrels = json.loads((ANN / "qrels_v1.json").read_text(encoding="utf-8"))
    data = []
    for nid, items in qrels.items():
        n = needs[nid]
        judgments = []
        for j in items:
            rec = {"alias": j["alias"], "family": j["family"], "article_no": j["article_no"], "grade": j["grade"], "basis": j["basis"], "round": j.get("round", 1)}
            if j["article_no"] is not None:
                for lang in ("ru", "kk"):
                    head, text = article_by_family(df, j["family"], j["article_no"], lang)
                    rec[f"heading_{lang}"] = head
                    rec[f"text_{lang}"] = (text or "")[:SNIPPET]
            judgments.append(rec)
        data.append({"id": nid, "type": n["type"], "topic": n["topic"], "ru": n["ru"], "kk": n["kk"], "en": n["en"], "judgments": judgments})
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = TEMPLATE.replace("/*DATA*/[]", payload)
    out = ANN / "review.html"
    out.write_text(html, encoding="utf-8")
    print("wrote", out, f"{out.stat().st_size / 1e3:.0f} KB,", len(data), "needs")


if __name__ == "__main__":
    main()
