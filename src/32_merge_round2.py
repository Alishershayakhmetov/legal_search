"""Merge the round-2 pooled judgments into annotation/qrels_v1.json.

Every candidate shown in annotation/pool_round2.json was read (heading and the start of the text). Candidates not
listed in ROUND2 were judged not relevant and are stored with grade 0, so a later evaluation can tell "judged
non-relevant" from "never judged". MANUAL lists articles read in full that the pool had not surfaced.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ANN = ROOT / "annotation"

# need -> {candidate index in pool_round2.json: grade}; unlisted candidates are grade 0
ROUND2 = {
    "L02": {0: 1, 1: 1, 5: 1}, "L04": {0: 1, 1: 1}, "L06": {0: 1, 3: 1}, "L07": {2: 1},
    "C03": {3: 1}, "C04": {3: 1, 4: 1}, "C06": {0: 2, 2: 1},
    "F01": {1: 1}, "F02": {0: 2, 2: 1, 3: 1, 4: 1}, "F03": {2: 1, 3: 1, 4: 1}, "F04": {0: 1, 1: 1, 2: 1, 3: 1, 5: 1},
    "T03": {4: 1}, "T05": {0: 1, 1: 1, 2: 1},
    "A02": {3: 1}, "A03": {1: 1}, "A04": {0: 1}, "K03": {1: 1}, "K04": {0: 1},
    "P01": {4: 1}, "P02": {2: 1, 3: 1}, "P03": {2: 1, 3: 2},
    "H01": {0: 1, 1: 1, 3: 1}, "H02": {0: 1, 1: 2, 2: 1}, "H03": {0: 2, 5: 1},
    "B01": {0: 1, 1: 1}, "B02": {0: 2}, "B03": {1: 1},
    "S01": {2: 1}, "S02": {0: 1, 2: 2, 5: 1}, "S04": {2: 2},
    "O03": {4: 1, 5: 1}, "O04": {1: 1}, "O05": {0: 1},
}
MANUAL = {  # need -> [(family, article_no, grade)], read in full
    "T03": [("о налогах и других обязательных платежах в бюджет (налоговый кодекс)", "528", 2),
            ("о налогах и других обязательных платежах в бюджет (налоговый кодекс)", "529", 1)],
    "K01": [("уголовный кодекс республики казахстан", "187", 1)],
    "K02": [("уголовный кодекс республики казахстан", "187", 1)],
}


def main():
    arts = load_articles()
    pool = json.loads((ANN / "pool_round2.json").read_text(encoding="utf-8"))
    qrels = json.loads((ANN / "qrels_v0.json").read_text(encoding="utf-8"))
    for items in qrels.values():
        for j in items:
            j["round"] = 1

    def make(fam, art_no, grade, basis, heading):
        kk = arts[(arts.family == fam) & (arts.lang == "kk") & (arts.article_no == art_no)]
        ru = arts[(arts.family == fam) & (arts.lang == "ru") & (arts.article_no == art_no)]
        return {"alias": fam[:42], "family": fam, "article_no": art_no, "grade": grade, "basis": basis, "round": 2,
                "heading_ru": heading, "heading_kk": kk.heading.iloc[0] if len(kk) else None,
                "law_ids": sorted(set(ru.law_id) | set(kk.law_id)), "has_kk": bool(len(kk))}

    added = {0: 0, 1: 0, 2: 0}
    for nid, entry in pool.items():
        known = {(j["family"], j["article_no"]) for j in qrels[nid]}
        for i, c in enumerate(entry["candidates"]):
            g = ROUND2.get(nid, {}).get(i, 0)
            if (c["family"], c["article_no"]) in known:
                continue
            qrels[nid].append(make(c["family"], c["article_no"], g, "pooled", c["heading"]))
            known.add((c["family"], c["article_no"]))
            added[g] += 1
        for fam, art_no, g in MANUAL.get(nid, []):
            if (fam, art_no) in known:
                continue
            head = arts[(arts.family == fam) & (arts.lang == "ru") & (arts.article_no == art_no)].heading.iloc[0]
            qrels[nid].append(make(fam, art_no, g, "read", head))
            known.add((fam, art_no))
            added[g] += 1
    (ANN / "qrels_v1.json").write_text(json.dumps(qrels, ensure_ascii=False, indent=1), encoding="utf-8")
    judged = [j for items in qrels.values() for j in items if j["article_no"] is not None]
    print("round-2 additions: grade 2:", added[2], "| grade 1:", added[1], "| grade 0 (judged not relevant):", added[0])
    print("articles judged in total:", len(judged), "| grade 2:", sum(j["grade"] == 2 for j in judged), "| grade 1:", sum(j["grade"] == 1 for j in judged),
          "| grade 0:", sum(j["grade"] == 0 for j in judged))


if __name__ == "__main__":
    main()
