"""Datasheets and checksums for the parallel corpus (D8) and the glossary (D10); numbers come from the build outputs. Nothing is published."""
import hashlib
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LICENCE = ("Status: **prepared locally, not published, no licence chosen yet.** The texts come from a CC BY 4.0 dataset (Mendeley, 'Textual Foundations of Justice'), so a derived "
           "release needs attribution to its authors; the author decides the licence before anything is published.")


def manifest(folder, files):
    lines = [f"{hashlib.sha256((folder / f).read_bytes()).hexdigest()}  {f}" for f in files]
    (folder / "MANIFEST.sha256").write_text(chr(10).join(lines) + chr(10), encoding="utf-8")


def main():
    st = json.loads((ROOT / "outputs" / "parallel_corpus.json").read_text(encoding="utf-8"))
    par = ROOT / "release" / "parallel"
    sheet = f"""# Datasheet: Russian-Kazakh parallel articles of Kazakhstani legislation

{LICENCE}

## Contents
`articles_ru_kk.parquet`: {st['pairs']:,} article pairs from {st['acts']:,} acts: the Russian and the Kazakh text of the same article (same act, same article number), with the act titles,
article headings, the cosine similarity of the two texts (bge-m3, first passage of each side), the ratio of text lengths, a tier and an `aligned` flag.
Tiers: high (cos >= 0.8) {st['tiers'].get('high', 0):,}; medium (0.7-0.8) {st['tiers'].get('medium', 0):,}; low (0.6-0.7) {st['tiers'].get('low', 0):,}; unreliable (< 0.6) {st['tiers'].get('unreliable', 0):,}.
`aligned` = cos >= 0.7 and length ratio between 0.5 and 2: {st['aligned']:,} pairs.

## How it was made
The Russian and Kazakh text files of the Mendeley dataset were linked to acts of the KazakhLawCorpus metadata by title, date and registry number (src/05_link_texts.py), cut into articles
(src/12_build_chunks.py), and articles of the same act with the same number were paired. Drafts and unlinked texts are excluded. The pairing is by article number, not by sentence.

## Alignment check (manual, small)
I read the first lines of 43 random pairs across the tiers: high 10 of 10 aligned; medium 8-9 of 9; low 5-6 of 9; unreliable about 4 of 15. Typical failures: treaties and annexes whose article numbers
repeat inside one file, a footnote passage paired with a full article, one text containing two articles. Use `aligned` or the `high` tier when precision matters. No second reader, no native-speaker review.

## Limitations and risks
Texts are a snapshot of 01.04.2024; they include footnotes and "Примечание ИЗПИ" notes. Some Kazakh texts use Latin look-alike letters (i) instead of Cyrillic 'і'. Long articles are only
checked on their first passage. Not suitable as a gold machine-translation benchmark without further review. Official texts: adilet.zan.kz. No personal data was searched for (legal texts contain
names of officials and, rarely, of private persons).
"""
    (par / "DATASHEET.md").write_text(sheet, encoding="utf-8")
    manifest(par, ["articles_ru_kk.parquet", "DATASHEET.md"])
    gl = ROOT / "release" / "glossary"
    ph, wd = pd.read_csv(gl / "glossary_phrases.csv"), pd.read_csv(gl / "glossary_words.csv")
    sheet = f"""# Datasheet: Russian-Kazakh legal term glossary (mined)

{LICENCE}

## Contents
* `glossary_phrases.csv`: {len(ph)} recurring article headings (in at least 3 acts) with one dominant Kazakh counterpart (columns: ru, kk, acts, pairs, consistency). Lower-cased, punctuation removed.
* `glossary_words.csv`: {len(wd)} word pairs: a Russian word and the Kazakh word that co-occurs with it most strongly in the headings of aligned articles (Dice >= 0.4, at least 8 heading pairs).
  Surface forms are the most frequent inflected forms, not dictionary forms; `kk_forms` lists the three most frequent Kazakh forms.

## How it was made
From the headings of the high-tier pairs of the parallel corpus (see its datasheet): whole-heading counting for the phrases; stem association (Russian Snowball stem x first five letters of the Kazakh word)
for the words. No dictionary or machine translation was used.

## Manual check (small, by me)
30 random phrases: all plausible translations. 50 random words: 46 correct or acceptable, 4 wrong because the two words only co-occur ("потребительского" - "кооперативінің", "тысяч" - "теңге",
"выписки" - "фактураларды", "причиняющей" - "дамуына"). Expect about 90% precision for words and higher for phrases; a native speaker has not reviewed it.

## Limitations
Heading vocabulary only (titles of articles), so the glossary is biased towards topics with many articles. Inflected forms. Kazakh letters normalised ('i' -> 'і').
"""
    (gl / "DATASHEET.md").write_text(sheet, encoding="utf-8")
    manifest(gl, ["glossary_phrases.csv", "glossary_words.csv", "DATASHEET.md"])
    print("datasheets written")


if __name__ == "__main__":
    main()
