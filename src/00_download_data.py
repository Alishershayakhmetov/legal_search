"""Download the raw data (metadata CSV and the two Mendeley archives), verify it and unpack the texts.

Every step is skipped when its result is already in place, so the script is safe to re-run:
  data/raw/kazakhlawcorpus/laws_metadata.csv        952 MB, Apache 2.0   (Hugging Face)
  data/archives/current.rar, kaz.rar                539 + 502 MB, CC BY 4.0 (Mendeley Data, SHA-256 checked)
  data/raw/mendeley_ru/current/*.txt, mendeley_kk/kaz/*.txt   unpacked texts (needs 7-Zip or unrar)
"""
import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
ARCHIVES = ROOT / "data" / "archives"
UA = "legal-search-student-project"

CSV = {
    "url": "https://huggingface.co/datasets/Arailym-tleubayeva/KazakhLawCorpus/resolve/main/data/laws_metadata.csv",
    "path": RAW / "kazakhlawcorpus" / "laws_metadata.csv",
    "size": 952_638_843,
}
MENDELEY = [
    {"name": "current.rar", "sha256": "31d4307f899bec69a1d51bff0704f733c56d2fde63567325910c27215139c63d", "target": RAW / "mendeley_ru", "files": 102_596,
     "url": "https://data.mendeley.com/public-files/datasets/jdpc5658nh/files/c838428d-13f8-42e7-ae86-dabe2c5de0a8/file_downloaded"},
    {"name": "kaz.rar", "sha256": "061e74685d3cdd3ccbca689c60cb0ebda1007f96ce20ceb3b170613e2d07d707", "target": RAW / "mendeley_kk", "files": 101_304,
     "url": "https://data.mendeley.com/public-files/datasets/jdpc5658nh/files/c99e62aa-4ee3-478d-bc1f-c3af58f44cfa/file_downloaded"},
]


def download(url, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".part")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    done, last = 0, 0
    with urllib.request.urlopen(req, timeout=60) as resp, open(tmp, "wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if done - last >= 100 << 20:
                print(f"  {path.name}: {done / 1e6:.0f} MB", flush=True)
                last = done
    tmp.replace(path)


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1 << 22):
            h.update(chunk)
    return h.hexdigest()


def count_txt(folder):
    return sum(1 for _ in folder.rglob("*.txt")) if folder.exists() else 0


def find_extractor():
    """Return (kind, executable) for 7-Zip or unrar, or None."""
    for name in ("7z", "7zz", "7za"):
        if shutil.which(name):
            return "7z", shutil.which(name)
    for candidate in ("C:/Program Files/7-Zip/7z.exe", "C:/Program Files (x86)/7-Zip/7z.exe"):
        if os.path.exists(candidate):
            return "7z", candidate
    if shutil.which("unrar"):
        return "unrar", shutil.which("unrar")
    return None


def extract(extractor, archive, target):
    kind, exe = extractor
    target.mkdir(parents=True, exist_ok=True)
    if kind == "7z":
        cmd = [exe, "x", "-y", "-bso0", "-bsp0", f"-o{target}", str(archive)]
    else:
        cmd = [exe, "x", "-y", "-idq", str(archive), str(target) + os.sep]
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skip-extract", action="store_true", help="download and verify only")
    args = ap.parse_args()

    if CSV["path"].exists() and CSV["path"].stat().st_size == CSV["size"]:
        print("metadata CSV: present, size matches")
    else:
        print("metadata CSV: downloading (952 MB)")
        download(CSV["url"], CSV["path"])
        if CSV["path"].stat().st_size != CSV["size"]:
            sys.exit(f"unexpected size of {CSV['path']}: {CSV['path'].stat().st_size}")

    for item in MENDELEY:
        path = ARCHIVES / item["name"]
        if not path.exists():
            print(f"{item['name']}: downloading")
            download(item["url"], path)
        digest = sha256(path)
        if digest != item["sha256"]:
            sys.exit(f"{item['name']}: SHA-256 mismatch ({digest}); delete the file and run again")
        print(f"{item['name']}: SHA-256 verified")

    if args.skip_extract:
        return
    extractor = find_extractor()
    for item in MENDELEY:
        have = count_txt(item["target"])
        if have >= item["files"]:
            print(f"{item['target'].name}: {have} text files already unpacked")
            continue
        if extractor is None:
            sys.exit("no extractor found: install 7-Zip (7z) or unrar, then run again")
        print(f"{item['name']}: unpacking to {item['target']}")
        extract(extractor, ARCHIVES / item["name"], item["target"])
        print(f"  {count_txt(item['target'])} text files")


if __name__ == "__main__":
    main()
