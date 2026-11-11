import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
META = ROOT / "data" / "interim" / "laws_metadata.parquet"
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed" / "act_text_link.parquet"
LANGS = {
    "ru": {"dir": RAW / "mendeley_ru", "title": "title_ru", "body": "adopting_body_ru", "region": "region_ru", "form": "act_form_ru"},
    "kk": {"dir": RAW / "mendeley_kk", "title": "title_kk", "body": "adopting_body_kk", "region": "region_kk", "form": "act_form_kk"},
}
KEYLEN = 5
MONTHS = {
    "ru": ["январ", "феврал", "март", "апрел", "ма[яй]", "июн", "июл", "август", "сентябр", "октябр", "ноябр", "декабр"],
    "kk": ["қаңтар", "ақпан", "наурыз", "сәуір", "мамыр", "маусым", "шілде", "тамыз", "қыркүйек", "қазан", "қараша", "желтоқсан"],
}
STATUS_LABELS = ("новый", "обновленный", "с истекшим", "исправление ошибки", "жаңа", "жаңартылған", "мерзімі біткен", "қатені")
FILLER = {"года", "г", "n", "no", "жылғы", "жыл", "жылы", "от", "за"}
MARGIN_DATE = 1.0
MARGIN_BODY = 1.5


def norm(s):
    s = s.lower().replace("ё", "е").replace("i", "і")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def key(s):
    return " ".join(s.split()[:KEYLEN])


def date_patterns(lang):
    mon = "(" + "|".join(f"({m})" for m in MONTHS[lang]) + ")"
    return [
        (re.compile(rf"(\d{{1,2}}) {mon}\w* (\d{{4}})"), "dmy"),
        (re.compile(rf"(\d{{4}}) жылғ\w* (\d{{1,2}}) {mon}\w*"), "ymd"),
    ]


PATTERNS = {lang: date_patterns(lang) for lang in MONTHS}


def month_index(m, lang):
    for i, pat in enumerate(MONTHS[lang]):
        if re.match(pat, m):
            return i + 1
    return None


def parse_dates(tail, lang):
    """Return [(iso_date, end_offset)] in order of appearance, without repeats."""
    found = []
    for pat, order in PATTERNS[lang]:
        for m in pat.finditer(tail):
            g = m.groups()
            d, mon, y = (g[0], g[1], g[-1]) if order == "dmy" else (g[1], g[2], g[0])
            mi = month_index(mon, lang)
            if mi:
                found.append((m.start(), f"{int(y):04d}-{mi:02d}-{int(d):02d}", m.end()))
    found.sort()
    seen, out = set(), []
    for _, d, end in found:
        if d not in seen:
            seen.add(d)
            out.append((d, end))
    return out


def number_follows(tail, end, reg):
    if not reg:
        return False
    tokens = [t for t in tail[end:].split()[:6]]
    while tokens and tokens[0] in FILLER:
        tokens.pop(0)
    return any("".join(tokens[:k]) == reg for k in (1, 2, 3))


def stems_of(text):
    return {w[:5] for w in norm(text).split() if len(w) >= 5}


def overlap(tail_stems, ref):
    return len(ref & tail_stems) / len(ref) if ref else 0.0


class Meta:
    """Per-language lookup tables built once from the metadata frame."""

    def __init__(self, df, lang):
        cfg = LANGS[lang]
        self.lang = lang
        self.ids = df["law_id"].tolist()
        self.date = df["date_adopted"].tolist()
        self.reg = [re.sub(r"[\W_]", "", norm(x)) for x in df["law_registry_number"]]
        self.body = [stems_of(b + " " + r) for b, r in zip(df[cfg["body"]], df[cfg["region"]])]
        self.form = [stems_of(x) for x in df[cfg["form"]]]
        self.by_title = defaultdict(list)
        self.by_key = defaultdict(set)
        for i, t in enumerate(df[cfg["title"]].tolist()):
            n = norm(t)
            if n:
                self.by_title[n].append(i)
                self.by_key[key(n)].add(n)

    @staticmethod
    def ends_at_label(n, title):
        """A title shorter than KEYLEN words is only trusted when a status label follows it directly."""
        return len(title.split()) >= KEYLEN or n[len(title) + 1:].startswith(STATUS_LABELS)

    def find_titles(self, n):
        words = n.split()
        pool = set()
        for k in range(1, KEYLEN + 1):
            pool |= self.by_key.get(" ".join(words[:k]), set())
        full = [t for t in pool if n == t or (n.startswith(t + " ") and self.ends_at_label(n, t))]
        if full:
            return max(full, key=len), False
        trunc = [t for t in pool if t.startswith(n)]
        return (trunc, True) if trunc else (None, False)

    def score(self, cands, tail):
        dates = parse_dates(tail, self.lang)
        tail_st = stems_of(tail)
        date_set = {d for d, _ in dates}
        out = []
        for i in cands:
            s = 0.0
            hit = self.date[i] in date_set
            num = False
            if hit:
                s += 4 if dates[0][0] == self.date[i] else 2
                end = next(e for d, e in dates if d == self.date[i])
                num = number_follows(tail, end, self.reg[i])
                s += 3 if num else 0
            s += 2 * overlap(tail_st, self.body[i]) + overlap(tail_st, self.form[i])
            out.append((s, i, hit, num))
        out.sort(reverse=True)
        return dates, out


def decide(cands_scored, ids):
    """Pick one act (or none) from scored candidates; returns (law_id, match_type, score)."""
    top = cands_scored[0]
    second = cands_scored[1][0] if len(cands_scored) > 1 else -1
    date_hits = [x for x in cands_scored if x[2]]
    num_hits = [x for x in date_hits if x[3]]
    if len(date_hits) == 1:
        return ids[date_hits[0][1]], "date_unique", date_hits[0][0]
    if len(num_hits) == 1:
        return ids[num_hits[0][1]], "date_number", num_hits[0][0]
    if date_hits and top[2] and top[0] - second >= MARGIN_DATE:
        return ids[top[1]], "date_body", top[0]
    if not date_hits and top[0] >= 2 and top[0] - second >= MARGIN_BODY:
        return ids[top[1]], "body_only", top[0]
    return None, "ambiguous", top[0]


def link_lang(df, lang):
    m = Meta(df, lang)
    cfg = LANGS[lang]
    rows = []
    for p in cfg["dir"].rglob("*.txt"):
        n = norm(p.stem)
        rec = {"lang": lang, "file": p.relative_to(RAW).as_posix(), "size": p.stat().st_size, "law_id": None,
               "match_type": "none", "n_cands": 0, "score": 0.0, "tail_date": None, "title_key": None}
        t, truncated = m.find_titles(n)
        if t is None:
            rows.append(rec)
            continue
        if truncated:
            cands = [i for tt in t for i in m.by_title[tt]]
            rec["n_cands"] = len(cands)
            if len(cands) == 1:
                rec.update(law_id=m.ids[cands[0]], match_type="truncated_unique")
            else:
                rec["match_type"] = "truncated_ambiguous"
            rows.append(rec)
            continue
        cands = m.by_title[t]
        rec["n_cands"] = len(cands)
        rec["title_key"] = t
        dates, scored = m.score(cands, n[len(t):])
        rec["tail_date"] = dates[0][0] if dates else None
        if len(cands) == 1:
            rec.update(law_id=m.ids[cands[0]], match_type="title_unique", score=scored[0][0])
        else:
            lid, mt, sc = decide(scored, m.ids)
            rec.update(law_id=lid, match_type=mt, score=sc)
        rows.append(rec)
    return pd.DataFrame(rows), m


def validate(df, m):
    """On title_unique files the act is known without date or number, so they act as a labelled check."""
    pos = {lid: i for i, lid in enumerate(m.ids)}
    d = df[(df.match_type == "title_unique") & df.tail_date.notna()]
    date_ok = sum(m.date[pos[l]] == t for l, t in zip(d.law_id, d.tail_date)) / max(len(d), 1)
    return len(d), date_ok


def main():
    meta = pd.read_parquet(META).reset_index(drop=True).fillna("")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = []
    for lang in LANGS:
        df, m = link_lang(meta, lang)
        parts.append(df)
        print(f"\n=== {lang}: {len(df)} files")
        print(df.match_type.value_counts().to_string())
        print("linked to an act:", f"{df.law_id.notna().mean():.1%}", "| distinct acts:", df.law_id.nunique())
        n, ok = validate(df, m)
        print(f"check on title_unique files with a parsed date: {n} files, tail date == date_adopted in {ok:.1%}")
    out = pd.concat(parts, ignore_index=True)
    out.to_parquet(OUT, index=False)
    ru = set(out[(out.lang == "ru") & out.law_id.notna()].law_id)
    kk = set(out[(out.lang == "kk") & out.law_id.notna()].law_id)
    print("\nacts with a ru text:", len(ru), "| kk text:", len(kk), "| both:", len(ru & kk))
    print("saved", OUT)


if __name__ == "__main__":
    main()
