"""Split a legal text into retrieval passages.

Acts with article headings (codes, laws) become one passage per article; everything else is packed
paragraph by paragraph. Long units are split on sentence boundaries, never inside a word.
"""
import hashlib
import re

MAX_CHARS = 1500
OVERLAP = 200
MIN_LETTERS = 25
MIN_ALPHA_RATIO = 0.45
MIN_ARTICLES = 3

ARTICLE = {
    # a heading is "Статья 5. Title" or just "Статья 5" on its own line (the Constitution and many treaties omit the period)
    "ru": re.compile(r"^Статья\s+(\d+(?:-\d+)?)(?:\.[ \t]*(.*)|[ \t]*)$", re.M),
    "kk": re.compile(r"^(\d+(?:-\d+)?)\s*-\s*бап(?:\.[ \t]*(.*)|[ \t]*)$", re.M | re.I),
}
SECTION = {
    "ru": re.compile(r"^((?:Глава|Раздел|Параграф)\s+\d+.*)$", re.M),
    "kk": re.compile(r"^(\d+\s*-\s*(?:тарау|б[өо]л[іiı]м|параграф).*)$", re.M | re.I),
}
KK_POINT = re.compile(r"\s1\.\s")
SENTENCE_END = re.compile(r"(?<=[.;:!?])\s+")
LETTER = re.compile(r"[^\W\d_]")


def clean(text):
    text = text.replace("\r", "").replace("\xa0", " ").replace("﻿", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"[ ]*\n[ ]*", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_long(unit):
    """Break a unit longer than MAX_CHARS on sentence ends, then on spaces as a last resort."""
    if len(unit) <= MAX_CHARS:
        return [unit]
    parts, cur = [], ""
    for sent in SENTENCE_END.split(unit):
        while len(sent) > MAX_CHARS:
            cut = sent.rfind(" ", 0, MAX_CHARS)
            cut = cut if cut > MAX_CHARS // 2 else MAX_CHARS
            if cur:
                parts.append(cur)
                cur = ""
            parts.append(sent[:cut])
            sent = sent[cut:].lstrip()
        if cur and len(cur) + 1 + len(sent) > MAX_CHARS:
            parts.append(cur)
            cur = sent
        else:
            cur = f"{cur} {sent}".strip()
    if cur:
        parts.append(cur)
    return parts


def pack(text):
    """Greedily pack lines into passages of at most MAX_CHARS, repeating a short last line as overlap."""
    units = [u for line in text.split("\n") if line.strip() for u in split_long(line.strip())]
    chunks, cur = [], []
    size = 0
    for u in units:
        if cur and size + 1 + len(u) > MAX_CHARS:
            chunks.append("\n".join(cur))
            carry = cur[-1] if len(cur[-1]) <= OVERLAP else None
            cur, size = ([carry], len(carry)) if carry else ([], 0)
        cur.append(u)
        size += len(u) + 1
    if cur:
        chunks.append("\n".join(cur))
    return chunks


def find_headings(text, lang):
    arts = [(m.start(), m.end(), "article", m.group(1), m.group(2) or "") for m in ARTICLE[lang].finditer(text)]
    secs = [(m.start(), m.end(), "section", None, m.group(1)) for m in SECTION[lang].finditer(text)]
    return sorted(arts + secs)


def segments(text, lang):
    """Yield (article_no, heading, section, body) in document order."""
    heads = find_headings(text, lang)
    n_art = sum(1 for h in heads if h[2] == "article")
    if n_art < MIN_ARTICLES:
        yield None, None, None, text
        return
    if heads[0][0] > 0:
        yield None, None, None, text[: heads[0][0]]
    section = None
    for i, (start, end, kind, no, title) in enumerate(heads):
        stop = heads[i + 1][0] if i + 1 < len(heads) else len(text)
        if kind == "section":
            section = title.strip()[:200]
            continue
        title = title.strip()
        if lang == "kk":
            title = KK_POINT.split(title, maxsplit=1)[0]
        yield no, title[:200], section, text[start:stop]


def keep(chunk):
    letters = len(LETTER.findall(chunk))
    return letters >= MIN_LETTERS and letters / len(chunk) >= MIN_ALPHA_RATIO


def is_table(chunk):
    lines = chunk.split("\n")
    return sum(" | " in ln or ln.startswith("|") for ln in lines) / len(lines) > 0.5


def chunk_text(text, lang):
    """Return (passages, stats). Each passage is a dict without file-level identifiers."""
    text = clean(text)
    stats = {"dropped": 0, "article_mode": 0}
    out = []
    pos = 0
    for article_no, heading, section, body in segments(text, lang):
        if article_no is not None:
            stats["article_mode"] = 1
        for piece in pack(body):
            if not keep(piece):
                stats["dropped"] += 1
                continue
            start = text.find(piece[:60], pos)
            if start >= 0:
                pos = start
            out.append({
                "article_no": article_no, "heading": heading, "section": section,
                "start_char": max(start, 0), "n_chars": len(piece), "is_table": is_table(piece), "text": piece,
                "text_hash": hashlib.md5(piece.encode("utf-8")).hexdigest(),
            })
    return out, stats
