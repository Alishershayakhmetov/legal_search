"""Turn the hand-checked judgments below into annotation/qrels_v0.json and annotation/queries.jsonl.

basis = "read": the article text was read and confirmed to answer (grade 2) or relate (grade 1) to the need.
basis = "heading": judged from the article heading only; to be confirmed in the review tool.
"""
import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "annotation"

spec = importlib.util.spec_from_file_location("fa", Path(__file__).with_name("16_find_anchors.py"))
fa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fa)
FAMILIES = fa.FAMILIES

# need -> [(family alias, article_no, grade)]
JUDGMENTS = {
    "L01": [("TK", "53", 2), ("TK", "52", 2), ("TK", "131", 2), ("TK", "54", 1)],
    "L02": [("TK", "88", 2), ("TK", "89", 1)],
    "L03": [("TK", "113", 2), ("KOAP", "87", 2), ("TK", "121", 1)],
    "L04": [("TK", "36", 2), ("TK", "37", 1)],
    "L05": [("TK", "78", 2), ("TK", "108", 2), ("TK", "77", 1)],
    "L06": [("TK", "99", 2), ("SOC", "77", 2), ("SOC", "78", 2)],
    "L07": [("TK", "109", 2), ("TK", "85", 1), ("TK", "86", 1)],
    "C01": [("GK_OB", "178", 2), ("GK_OB", "177", 1)],
    "C02": [("GK_OS", "546", 2), ("GK_OS", "556", 1), ("GK_OS", "545", 1)],
    "C03": [("GK_OS", "716", 2), ("GK_OS", "722", 2), ("GK_OS", "715", 1)],
    "C04": [("GK_OS", "1061", 2), ("GK_OS", "1062", 2), ("GK_OS", "1063", 1)],
    "C06": [("POTR", "15", 2), ("POTR", "30", 1)],
    "F01": [("SEM", "139", 2), ("SEM", "141", 1), ("SEM", "140", 1)],
    "F02": [("SEM", "19", 2), ("SEM", "17", 1), ("SEM", "16", 1)],
    "F03": [("SEM", "37", 2), ("SEM", "38", 2)],
    "F04": [("SEM", "91", 2), ("SEM", "92", 1), ("SEM", "84", 1), ("SEM", "87", 1)],
    "T01": [("NK", "320", 2), ("NK", "351", 1)],
    "T02": [("NK", "422", 2)],
    "T03": [("NK", "531", 2), ("NK", "492", 2)],
    "T05": [("NK", "610", 2), ("NK", "616", 1)],
    "A01": [("KOAP", "592", 2)],
    "A02": [("KOAP", "608", 2), ("UK", "345-1", 1)],
    "A03": [("KOAP", "441", 2), ("KOAP", "441-1", 1)],
    "A04": [("KOAP", "434", 2), ("KOAP", "435", 1)],
    "K01": [("UK", "188", 2)],
    "K02": [("UK", "190", 2)],
    "K03": [("UK", "32", 2), ("UK", "66", 1)],
    "K04": [("UK", "15", 2)],
    "P01": [("GPK", "403", 2)],
    "P02": [("GPK", "148", 2), ("GPK", "29", 1)],
    "P03": [("UPK", "64", 2), ("UPK", "131", 1), ("UPK", "128", 1)],
    "H01": [("ZK", "37", 2)],
    "H02": [("ZK", "86", 2), ("ZK", "85", 1), ("ZK", "84", 1)],
    "H03": [("JIL", "32", 2), ("JIL", "6", 1), ("JIL", "33", 1)],
    "B01": [("PK", "36", 2), ("PK", "35", 1), ("PK", "30", 1), ("PK", "37", 1)],
    "B02": [("TOO", "23", 2), ("TOO", "2", 1)],
    "B03": [("BANKR", "5", 2), ("BANKR", "6", 2), ("BANKR", "4", 1)],
    "S01": [("SOC", "207", 2), ("SOC", "208", 1)],
    "S02": [("SOC", "79", 2), ("SOC", "80", 2), ("SOC", "81", 1)],
    "S03": [("ZDR", "196", 2)],
    "S04": [("OBR", "31", 2), ("OBR", "16", 1)],
    "O01": [("PD", "8", 2), ("PD", "9", 2)],
    "O03": [("ISP", "95", 2), ("ISP", "93", 1), ("ISP", "94", 1)],
    "O04": [("VYBORY", "4", 2)],
    "O05": [("ADV", "26", 2), ("ADV", "18", 1)],
    # title needs are judged at act level: any article of the family counts
    "N01": [("PD", None, 2)], "N02": [("TK", None, 2)], "N03": [("NK", None, 2)], "N04": [("KOAP", None, 2)],
    "N05": [("ZK", None, 2)], "N06": [("POTR", None, 2)], "N07": [("SEM", None, 2)], "N08": [("SOC", None, 2)],
}

DROPPED = {
    "C05": "no article on the sale of dwellings found in the extracted Civil Code (Special part)",
    "T04": "no article on a tax deduction for buying a home found in the Tax Code text",
    "O02": "no provision on days of stay without registration found in the migration law text",
}

READ = {
    ("TK", "36"), ("TK", "52"), ("TK", "53"), ("TK", "54"), ("TK", "88"), ("TK", "99"), ("TK", "113"), ("TK", "78"),
    ("TK", "131"), ("TK", "108"), ("TK", "109"), ("KOAP", "87"), ("KOAP", "592"), ("KOAP", "608"), ("KOAP", "441"),
    ("KOAP", "434"), ("UK", "188"), ("UK", "190"), ("UK", "32"), ("UK", "15"), ("SEM", "139"), ("SEM", "37"),
    ("SEM", "91"), ("POTR", "15"), ("ZDR", "196"), ("SOC", "207"), ("SOC", "79"), ("SOC", "80"), ("SOC", "77"),
    ("NK", "320"), ("NK", "531"), ("NK", "422"), ("NK", "492"), ("NK", "610"), ("PD", "8"), ("PD", "9"),
    ("ISP", "95"), ("JIL", "32"), ("BANKR", "5"), ("BANKR", "6"), ("PK", "36"), ("ZK", "37"), ("ZK", "86"),
    ("GK_OB", "178"), ("GK_OS", "546"), ("GK_OS", "556"), ("GK_OS", "716"), ("GK_OS", "722"), ("GPK", "403"),
    ("ADV", "26"), ("TOO", "23"), ("OBR", "31"), ("UPK", "64"), ("VYBORY", "4"),
}


def main():
    df = load_articles()
    needs = {n["id"]: n for n in json.loads((ANN / "needs.json").read_text(encoding="utf-8"))}
    missing = set(needs) - set(JUDGMENTS) - set(DROPPED)
    assert not missing, f"needs without judgments: {missing}"
    qrels, problems = {}, []
    for nid, items in JUDGMENTS.items():
        out = []
        for alias, art, grade in items:
            fam = FAMILIES[alias]
            sub = df[df.family == fam]
            laws = sorted(sub.law_id.unique())
            if art is None:
                out.append({"alias": alias, "family": fam, "article_no": None, "grade": grade, "basis": "title",
                            "law_ids": laws, "has_ru": bool((sub.lang == "ru").any()), "has_kk": bool((sub.lang == "kk").any())})
                continue
            ru = sub[(sub.lang == "ru") & (sub.article_no == art)]
            kk = sub[(sub.lang == "kk") & (sub.article_no == art)]
            if ru.empty:
                problems.append((nid, alias, art, "missing in ru"))
                continue
            out.append({
                "alias": alias, "family": fam, "article_no": art, "grade": grade,
                "basis": "read" if (alias, art) in READ else "heading",
                "heading_ru": ru.heading.iloc[0], "heading_kk": kk.heading.iloc[0] if len(kk) else None,
                "law_ids": sorted(ru.law_id.unique()), "has_kk": bool(len(kk)),
            })
        qrels[nid] = out
    (ANN / "qrels_v0.json").write_text(json.dumps(qrels, ensure_ascii=False, indent=1), encoding="utf-8")
    (ANN / "dropped.json").write_text(json.dumps(DROPPED, ensure_ascii=False, indent=1), encoding="utf-8")
    n_q = 0
    with open(ANN / "queries.jsonl", "w", encoding="utf-8") as f:
        for nid in qrels:
            n = needs[nid]
            for lang in ("ru", "kk", "en"):
                f.write(json.dumps({"query_id": f"{nid}-{lang}", "need_id": nid, "lang": lang, "type": n["type"],
                                    "topic": n["topic"], "text": n[lang]}, ensure_ascii=False) + "\n")
                n_q += 1
    allj = [j for items in qrels.values() for j in items if j["article_no"] is not None]
    print(f"needs: {len(qrels)} (+{len(DROPPED)} dropped) | queries: {n_q} | article judgments: {len(allj)}")
    print("grade 2:", sum(j["grade"] == 2 for j in allj), "| grade 1:", sum(j["grade"] == 1 for j in allj))
    print("basis read:", sum(j["basis"] == "read" for j in allj), "| heading only:", sum(j["basis"] == "heading" for j in allj))
    print("judged articles missing a Kazakh text:", [(n, j["alias"], j["article_no"]) for n, js in qrels.items() for j in js if j["article_no"] and not j["has_kk"]])
    print("title needs without kk text:", [(n, j["alias"]) for n, js in qrels.items() for j in js if j["article_no"] is None and not j["has_kk"]])
    print("problems:", problems)
    by_type = {}
    for n in qrels:
        by_type[needs[n]["type"]] = by_type.get(needs[n]["type"], 0) + 1
    print("needs by type:", by_type)


if __name__ == "__main__":
    main()
