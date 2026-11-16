"""Amendment history and pending changes of an article, read from the notes that the source texts already contain.

Footnotes ("Сноска. Статья 9 с изменениями, внесенными Законом РК от 21.07.2015 № 337-V (вводится в действие ...)", Kazakh "Ескерту. ...")
list the acts that changed the article. Notes "Примечание ИЗПИ!" / "ЗҚАИ-ның ескертпесі!" announce changes that were not yet in force when
the texts were taken (01.04.2024). Everything here is plain text parsing; nothing is looked up elsewhere, so an article whose notes are
missing or phrased unusually shows no history, which does not mean it was never changed.
"""
import re
from datetime import date

SNAPSHOT = date(2024, 4, 1)  # the corpus texts are as of this day
FOOTNOTE = re.compile(r"^(Сноска|Ескерту)\.\s*(.*)$")
PENDING_MARK = re.compile(r"^(Примечание ИЗПИ!|ЗҚАИ-ның ескертпесі!)\s*(.*)$")
REF = re.compile(r"(\d{2}\.\d{2}\.\d{4}|\d{4}\.\d{2}\.\d{2})\.?\s*(?:г\.|ж\.)?\s*[№N]\s*(\d+(?:-[IVXLCDMІ]+)?)")
ABS_DATE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
PAREN = re.compile(r"\(([^()]{0,260})\)")
ACTIONS = (("new_edition", re.compile(r"в\s+(?:новой\s+)?редакции|жаңа\s+редакцияда", re.I)),
           ("added", re.compile(r"дополнен|толықтырылды", re.I)),
           ("removed", re.compile(r"исключен|признан[аы]?\s+утратив|алып\s+тасталды|күші\s+жойылды", re.I)),
           ("changed", re.compile(r"изменени|изменен|өзгеріс|өзгертілді", re.I)))
ACTION_LABEL = {"new_edition": "новая редакция", "added": "дополнено", "removed": "исключено", "changed": "изменено", None: "изменено"}
ACTION_LABEL_KK = {"new_edition": "жаңа редакция", "added": "толықтырылды", "removed": "алып тасталды", "changed": "өзгертілді", None: "өзгертілді"}
RELATIVE_WORDS = {"десяти": 10, "тридцати": 30, "шестидесяти": 60, "девяноста": 90, "двадцати": 20, "пятнадцати": 15, "сорока": 40,
                  "он күн": 10, "отыз күн": 30, "алпыс күн": 60, "тоқсан күн": 90, "жиырма күн": 20, "он бес күн": 15}


MONTHS = {m: i for i, m in enumerate("января февраля марта апреля мая июня июля августа сентября октября ноября декабря".split(), 1)}
VERBAL_DATE = re.compile(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})(?:\s*(?:года|г\.))?")


def numeric_dates(text):
    """'7 июля 2006 года' -> '07.07.2006' (older footnotes spell dates out)."""
    return VERBAL_DATE.sub(lambda m: f"{int(m.group(1)):02d}.{MONTHS[m.group(2)]:02d}.{m.group(3)}", text)


def to_date(s):
    """'21.07.2015' or '2005.07.08' -> date, or None."""
    try:
        if re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", s):
            y, m, d = s.split(".")
        else:
            d, m, y = s.split(".")
        return date(int(y), int(m), int(d))
    except ValueError:
        return None


def entry_into_force(parenthesis):
    """(absolute date or None, short human text or None) from the bracket that follows a reference."""
    if not parenthesis:
        return None, None
    m = ABS_DATE.search(parenthesis)
    if m and ("действие" in parenthesis or "қолданыс" in parenthesis or "күшіне" in parenthesis or "силу" in parenthesis):
        d = to_date(m.group(0))
        if d:
            return d, f"с {d:%d.%m.%Y}"
    if re.search(r"порядок\s+введения|тәртібін|см\.\s*ст", parenthesis, re.I):
        return None, "порядок введения в действие определён отдельной статьёй закона"
    low = parenthesis.lower()
    n = next((v for k, v in RELATIVE_WORDS.items() if re.search(r"(?<![\wіқғңөүұһәё])" + k + r"(?![\wіқғңөүұһәё])", low)), None)
    num = re.search(r"(\d+)\s+(?:календарн|күнтіз)", low)
    days = int(num.group(1)) if num else n
    if days and ("опубликован" in low or "жарияланған" in low):
        return None, f"через {days} календарных дней после первого официального опубликования"
    if "бастап" in low and "жарияланған" in low:
        return None, "со дня первого официального опубликования"
    if "опубликован" in low or "жарияланған" in low:
        return None, "после первого официального опубликования"
    return None, parenthesis.strip()[:90] or None


def parse_footnote(line, lang="ru"):
    """List of {'date', 'number', 'action', 'effective_date', 'effective'} for one footnote paragraph."""
    body = numeric_dates(FOOTNOTE.sub(r"\2", line, count=1))
    labels = ACTION_LABEL_KK if lang == "kk" else ACTION_LABEL
    entries, inherited = [], None
    for clause in re.split(r";\s*", body):
        m = REF.search(clause)
        if not m:
            continue
        explicit = next((name for name, rx in ACTIONS if rx.search(clause[:m.start()])), None)
        action = explicit or inherited
        inherited = action  # a later clause without its own verb continues the last one
        tail = clause[m.end():]
        par = PAREN.search(tail)
        eff_date, eff_text = entry_into_force(par.group(1) if par else None)
        entries.append({"date": m.group(1), "number": m.group(2), "action": labels[action], "effective_date": eff_date.isoformat() if eff_date else None,
                        "effective": eff_text})
    return entries


def parse_notes(text, lang="ru", today=None):
    """{'history': [...], 'pending': [...]} for the text of one article; pending items carry a status for today's date."""
    today = today or date.today()
    history, pending = [], []
    lines = [numeric_dates(ln.strip()) for ln in text.split(chr(10))]
    for i, ln in enumerate(lines):
        if FOOTNOTE.match(ln):
            history += parse_footnote(ln, lang)
        else:
            m = PENDING_MARK.match(ln)
            if m:
                note = m.group(2).strip()
                j = i + 1
                while not note and j < len(lines):  # the note is on the next line; consecutive markers share the text that follows
                    if lines[j] and not PENDING_MARK.match(lines[j]):
                        note = lines[j]
                    j += 1
                if not note:
                    continue
                refs = REF.search(note)
                par = PAREN.search(note[refs.end():]) if refs else None
                eff_date, eff_text = entry_into_force(par.group(1) if par else None)
                pending.append({"note": note[:400], "date": refs.group(1) if refs else None, "number": refs.group(2) if refs else None,
                                "effective_date": eff_date.isoformat() if eff_date else None, "effective": eff_text})
    for h in history:  # a footnote entry that takes effect after the text was taken is also a pending change
        if h["effective_date"] and date.fromisoformat(h["effective_date"]) > SNAPSHOT:
            pending.append({"note": f"{h['action']} — акт от {h['date']} № {h['number']}", "date": h["date"], "number": h["number"],
                            "effective_date": h["effective_date"], "effective": h["effective"]})
    for p in pending:
        d = date.fromisoformat(p["effective_date"]) if p["effective_date"] else None
        p["status"] = "unknown" if d is None else ("upcoming" if d > today else ("in_force_since_snapshot" if d > SNAPSHOT else "in_force"))
    pending = [p for p in pending if p["status"] != "in_force"]
    seen, unique = set(), []
    for p in pending:
        key = (p["note"][:80], p["effective_date"])
        if key not in seen:
            seen.add(key)
            unique.append(p)
    first = {}
    for h in history:  # the same footnote can appear in several passages of one article
        first.setdefault((h["date"], h["number"], h["action"]), h)
    history = sorted(first.values(), key=lambda h: to_date(h["date"]) or date.min)
    return {"history": history, "pending": unique}
