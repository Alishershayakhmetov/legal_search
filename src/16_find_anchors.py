import json
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annotation_tools import load_articles  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

FAMILIES = {
    "TK": "трудовой кодекс республики казахстан",
    "GK_OB": "гражданский кодекс республики казахстан",
    "GK_OS": "гражданский кодекс республики казахстан (особенная часть)",
    "SEM": "о браке (супружестве) и семье",
    "NK": "о налогах и других обязательных платежах в бюджет (налоговый кодекс)",
    "KOAP": "об административных правонарушениях",
    "UK": "уголовный кодекс республики казахстан",
    "UPK": "уголовно-процессуальный кодекс республики казахстан",
    "GPK": "гражданский процессуальный кодекс республики казахстан",
    "ZK": "земельный кодекс республики казахстан",
    "JIL": "о жилищных отношениях",
    "PK": "предпринимательский кодекс республики казахстан",
    "TOO": "о товариществах с ограниченной и дополнительной ответственностью",
    "BANKR": "о восстановлении платежеспособности и банкротстве граждан республики казахстан",
    "SOC": "социальный кодекс республики казахстан",
    "ZDR": "о здоровье народа и системе здравоохранения",
    "OBR": "об образовании",
    "PD": "о персональных данных и их защите",
    "MIGR": "о миграции населения",
    "ISP": "об исполнительном производстве и статусе судебных исполнителей",
    "POTR": "о защите прав потребителей",
    "VYBORY": "о выборах в республике казахстан",
    "ADV": "об адвокатской деятельности и юридической помощи",
}


def candidates(df, alias, pattern, limit=14):
    ru = df[(df.lang == "ru") & (df.family == FAMILIES[alias])]
    heads = ru.drop_duplicates(["article_no"])[["article_no", "heading"]].copy()
    heads["heading"] = heads.heading.fillna("")
    hit = heads[heads.heading.str.contains(pattern, flags=re.I, regex=True)] if pattern else heads.head(0)
    return hit.head(limit), heads.shape[0]


def main():
    df = load_articles()
    needs = json.loads((ROOT / "annotation" / "needs.json").read_text(encoding="utf-8"))
    only = set(sys.argv[1:])
    for n in needs:
        if only and n["id"] not in only:
            continue
        if n["type"] == "title":
            continue
        print(f"\n## {n['id']}  {n['ru']}")
        for alias, pat in n["anchors"]:
            hit, total = candidates(df, alias, pat)
            print(f"  [{alias}] /{pat}/ -> {len(hit)} shown of {total} articles")
            for r in hit.itertuples():
                print(f"     ст.{r.article_no:<7} {r.heading[:100]}")


if __name__ == "__main__":
    main()
