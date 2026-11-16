# Datasheet: Russian-Kazakh parallel articles of Kazakhstani legislation

Status: **prepared locally, not published, no licence chosen yet.** The texts come from a CC BY 4.0 dataset (Mendeley, 'Textual Foundations of Justice'), so a derived release needs attribution to its authors; the author decides the licence before anything is published.

## Contents
`articles_ru_kk.parquet`: 40,516 article pairs from 2,139 acts: the Russian and the Kazakh text of the same article (same act, same article number), with the act titles,
article headings, the cosine similarity of the two texts (bge-m3, first passage of each side), the ratio of text lengths, a tier and an `aligned` flag.
Tiers: high (cos >= 0.8) 35,426; medium (0.7-0.8) 4,668; low (0.6-0.7) 330; unreliable (< 0.6) 92.
`aligned` = cos >= 0.7 and length ratio between 0.5 and 2: 39,541 pairs.

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
