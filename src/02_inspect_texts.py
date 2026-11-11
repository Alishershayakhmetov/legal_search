import re
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIRS = {"ru": ROOT / "data" / "raw" / "mendeley_ru", "kk": ROOT / "data" / "raw" / "mendeley_kk"}
ARTICLE = {"ru": re.compile(r"^\s*Статья\s+\d+", re.M), "kk": re.compile(r"^\s*\d+-\s*бап|^\s*\d+-бап", re.M | re.I)}


def list_files(base):
    return [p for p in base.rglob("*") if p.is_file()]


def read(p):
    raw = p.read_bytes()
    for enc in ("utf-8-sig", "cp1251"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace"), "replace"


def main():
    for lang, base in DIRS.items():
        files = list_files(base)
        sizes = [p.stat().st_size for p in files]
        print(f"\n=== {lang}: {len(files)} files, {sum(sizes) / 1e9:.2f} GB, "
              f"median {statistics.median(sizes) / 1e3:.1f} KB, max {max(sizes) / 1e6:.1f} MB")
        print("subdirs:", sorted({p.parent.relative_to(base).as_posix() for p in files})[:5])
        print("suffixes:", {p.suffix for p in files})
        sample = files[:: max(1, len(files) // 400)]
        encs, with_art, lens = {}, 0, []
        for p in sample:
            t, e = read(p)
            encs[e] = encs.get(e, 0) + 1
            lens.append(len(t))
            if ARTICLE[lang].search(t):
                with_art += 1
        print("encodings:", encs, "| with article headings:", with_art, "/", len(sample))
        print("sample names:")
        for p in sample[:5]:
            print("  ", p.name[:120])
        big = max(files, key=lambda p: p.stat().st_size)
        print("largest:", big.name[:100], big.stat().st_size // 1000, "KB")
        mid = sample[len(sample) // 3]
        t, _ = read(mid)
        print("--- head of", mid.name[:80])
        print(t[:900])


if __name__ == "__main__":
    main()
