import random
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RU = ROOT / "data" / "raw" / "mendeley_ru" / "current"
KK = ROOT / "data" / "raw" / "mendeley_kk" / "kaz"

PATTERNS = {
    "ru_article": re.compile(r"^\s*Статья\s+\d+(-\d+)?\.", re.M),
    "ru_chapter": re.compile(r"^\s*(Глава|Раздел|Параграф|Часть)\s+\d+", re.M),
    "ru_point": re.compile(r"^\s*\d+\.\s+\S", re.M),
    "kk_article": re.compile(r"^\s*\d+(-\d+)?-\s*бап\b", re.M | re.I),
    "kk_chapter": re.compile(r"^\s*\d+-\s*(тарау|бөлім|параграф)", re.M | re.I),
    "kk_point": re.compile(r"^\s*\d+\.\s+\S", re.M),
    "table_bar": re.compile(r"\|"),
}


def read(p):
    return p.read_text(encoding="utf-8-sig", errors="replace")


def sample(base, n, seed):
    files = sorted(base.glob("*.txt"))
    random.Random(seed).shuffle(files)
    return files[:n]


def main():
    for lang, base in (("ru", RU), ("kk", KK)):
        files = sample(base, 3000, 7)
        c = Counter()
        lens = []
        for p in files:
            t = read(p)
            lens.append(len(t))
            for k, pat in PATTERNS.items():
                if k.startswith(lang) or k == "table_bar":
                    if pat.search(t):
                        c[k] += 1
            if t.count("\n\n") < 2:
                c["few_paragraphs"] += 1
            if len(t) > 100_000:
                c["over_100k_chars"] += 1
        print(f"\n=== {lang}: {len(files)} sampled; chars median {sorted(lens)[len(lens) // 2]}, max {max(lens)}")
        print(dict(c))

    for label, base, prefix in (("ru code", RU, "Трудовой кодекс Республики Казахстан"), ("kk code", KK, "Қазақстан Республикасының Еңбек кодексі")):
        hits = [p for p in base.glob("*.txt") if p.stem.strip().startswith(prefix)]
        print(f"\n--- {label}: {len(hits)} files for prefix {prefix!r}")
        if hits:
            p = max(hits, key=lambda x: x.stat().st_size)
            t = read(p)
            print(p.name[:100], len(t), "chars")
            heads = [m.group(0).strip() for m in PATTERNS["ru_article" if "ru" in label else "kk_article"].finditer(t)]
            print("article headings:", len(heads), heads[:4])
            i = t.find("Статья 52" if "ru" in label else "52-бап")
            print(repr(t[max(0, i - 100): i + 700]))


if __name__ == "__main__":
    main()
