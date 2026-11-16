# Datasheet: Russian-Kazakh legal term glossary (mined)

Status: **prepared locally, not published, no licence chosen yet.** The texts come from a CC BY 4.0 dataset (Mendeley, 'Textual Foundations of Justice'), so a derived release needs attribution to its authors; the author decides the licence before anything is published.

## Contents
* `glossary_phrases.csv`: 204 recurring article headings (in at least 3 acts) with one dominant Kazakh counterpart (columns: ru, kk, acts, pairs, consistency). Lower-cased, punctuation removed.
* `glossary_words.csv`: 1174 word pairs: a Russian word and the Kazakh word that co-occurs with it most strongly in the headings of aligned articles (Dice >= 0.4, at least 8 heading pairs).
  Surface forms are the most frequent inflected forms, not dictionary forms; `kk_forms` lists the three most frequent Kazakh forms.

## How it was made
From the headings of the high-tier pairs of the parallel corpus (see its datasheet): whole-heading counting for the phrases; stem association (Russian Snowball stem x first five letters of the Kazakh word)
for the words. No dictionary or machine translation was used.

## Manual check (small, by me)
30 random phrases: all plausible translations. 50 random words: 46 correct or acceptable, 4 wrong because the two words only co-occur ("потребительского" - "кооперативінің", "тысяч" - "теңге",
"выписки" - "фактураларды", "причиняющей" - "дамуына"). Expect about 90% precision for words and higher for phrases; a native speaker has not reviewed it.

## Limitations
Heading vocabulary only (titles of articles), so the glossary is biased towards topics with many articles. Inflected forms. Kazakh letters normalised ('i' -> 'і').
