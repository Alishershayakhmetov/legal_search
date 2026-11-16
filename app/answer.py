"""A short answer written by a language model from retrieved articles only, with every sentence checked before it is shown.

Pipeline: pick excerpts (the sentences of the top articles closest to the question) -> prompt the model to answer only from them with
[n] citations -> split the answer into sentences -> keep a sentence only if (1) it cites an existing excerpt, (2) every number in it
occurs in a cited excerpt (digits or spelled-out Russian/Kazakh numbers), (3) its meaning is close to a sentence of a cited excerpt
(bge-m3 cosine above a threshold calibrated in src/46_answer_eval.py). Sentences that fail are dropped and counted; if none is left no
answer is shown. This lowers the risk of invented citations and figures; it does not make the answer legal advice.
"""
import re
import time

import numpy as np

CITE = re.compile(r"\[(\d+(?:\s*[,;]\s*\d+)*)\]")
NO_ANSWER = re.compile(r"^\W*(НЕТ ОТВЕТА|NO ANSWER|ЖАУАП ЖОҚ)", re.I)
# Support thresholds (cosine of bge-m3 between an answer sentence and the closest sentence of a cited excerpt), per answer language.
# Calibrated in src/46_answer_eval.py: 0.65 is about the 5th percentile of true citations and the 95th of the control (outputs/answer_eval.json).
SUPPORT_MIN = {"ru": 0.65, "kk": 0.65, "en": 0.65}

UNITS = {"два": 2, "двух": 2, "две": 2, "три": 3, "трех": 3, "трёх": 3, "четыре": 4, "четырех": 4, "четырёх": 4,
         "пять": 5, "пяти": 5, "шесть": 6, "шести": 6, "семь": 7, "семи": 7, "восемь": 8, "восьми": 8, "девять": 9, "девяти": 9, "десять": 10, "десяти": 10,
         "одиннадцать": 11, "двенадцать": 12, "пятнадцать": 15, "екі": 2, "үш": 3, "төрт": 4, "бес": 5, "алты": 6, "жеті": 7, "сегіз": 8, "тоғыз": 9}
TENS = {"двадцать": 20, "двадцати": 20, "тридцать": 30, "тридцати": 30, "сорок": 40, "сорока": 40, "пятьдесят": 50, "пятидесяти": 50, "шестьдесят": 60,
        "шестидесяти": 60, "семьдесят": 70, "семидесяти": 70, "восемьдесят": 80, "восьмидесяти": 80, "девяносто": 90, "девяноста": 90, "сто": 100, "ста": 100,
        "жиырма": 20, "отыз": 30, "қырық": 40, "елу": 50, "алпыс": 60, "жетпіс": 70, "сексен": 80, "тоқсан": 90, "жүз": 100}
WORD = re.compile(r"[\w]+", re.U)


def numbers_in(text):
    """All integers in a text: digit groups and spelled-out numbers ('двадцати четырех' -> 24, 'жиырма төрт' -> 24)."""
    found = {int(x) for x in re.findall(r"\d+", text)}
    words = [w.lower() for w in WORD.findall(text)]
    i = 0
    while i < len(words):
        w = words[i]
        if w in TENS:
            val = TENS[w]
            if i + 1 < len(words) and words[i + 1] in UNITS and UNITS[words[i + 1]] < 10:
                found.add(val + UNITS[words[i + 1]])
                i += 1
            found.add(val)
        elif w in UNITS:
            found.add(UNITS[w])
        i += 1
    return found


def prompt_for(query, excerpts, lang):
    answer_lang = {"ru": "на русском языке", "kk": "на казахском языке (қазақша)", "en": "in English"}[lang]
    system = ("Ты помощник по законодательству Республики Казахстан. Отвечай ТОЛЬКО по приведённым выдержкам из законов; не используй знания вне выдержек. "
              "После каждого предложения ответа ставь ссылку на выдержку в виде [1] или [1][2]. Не придумывай цифры, сроки и номера статей, которых нет в выдержках. "
              f"Ответ — не более 90 слов, {answer_lang}. Если выдержки не отвечают на вопрос, ответь ровно: НЕТ ОТВЕТА.")
    body = "\n\n".join(f"[{e['n']}] {e['title']}, ст. {e['article_no']}\n{e['text']}" for e in excerpts)
    tail = {"ru": "Ответ:", "kk": "Жауап (қазақша):", "en": "Answer (write the answer in English, not in Russian):"}[lang]
    return system, f"Выдержки:\n\n{body}\n\nВопрос: {query}\n\n{tail}"


def split_answer(text):
    """Sentences of the model's answer as [{'text', 'cites': [n, ...]}]; a fragment that is only a citation joins the previous sentence."""
    text = re.sub(r"\s+", " ", text.strip())
    parts = re.split(r"(?<=[.!?])\s+(?=[A-ZА-ЯЁӘҒҚҢӨҰҮҺІ«\"(\d\[])", text)
    merged = []
    for p in parts:
        lead = re.match(r"^((?:\[\d+(?:\s*[,;]\s*\d+)*\]\s*)+)(.*)$", p)
        if merged and lead:  # "... дней. [2] Следующее предложение": the citation belongs to the sentence before it
            merged[-1] += " " + lead.group(1).strip()
            p = lead.group(2).strip()
            if not p or re.fullmatch(r"[.!?]+", p):
                continue
        merged.append(p)
    out = []
    for s in merged:
        cites = sorted({int(n) for g in CITE.findall(s) for n in re.findall(r"\d+", g)})
        out.append({"text": s, "cites": cites})
    return out


def verify(sentences, excerpts, embed, lang, tau=None):
    """Mark each sentence ok / not ok with reasons. embed(list[str]) -> L2-normalised float matrix."""
    by_n = {e["n"]: e for e in excerpts}
    tau = SUPPORT_MIN.get(lang, 0.5) if tau is None else tau
    ex_sentences = {n: [s for s in re.split(r"(?<=[.;:])\s+|\n+", e["text"]) if len(s.strip()) >= 15] or [e["text"]] for n, e in by_n.items()}
    for s in sentences:
        reasons = []
        body = CITE.sub("", s["text"]).strip()
        if not s["cites"]:
            reasons.append("нет ссылки на выдержку")
        elif any(n not in by_n for n in s["cites"]):
            reasons.append("ссылка на несуществующую выдержку")
        cited = [by_n[n] for n in s["cites"] if n in by_n]
        if cited:
            allowed = set()
            for e in cited:
                allowed |= numbers_in(e["text"]) | numbers_in(str(e["article_no"]))
            missing = sorted(n for n in numbers_in(body) if n not in allowed)
            if missing:
                reasons.append("числа нет в цитируемых выдержках: " + ", ".join(map(str, missing)))
            cand = [x for e in cited for x in ex_sentences[e["n"]]]
            sims = embed([body] + cand)
            sc = sims[1:] @ sims[0]
            s["support"] = round(float(sc.max()), 3)
            s["support_quote"] = cand[int(sc.argmax())].strip()
            if s["support"] < tau:
                reasons.append(f"смысл не подтверждён выдержкой (близость {s['support']:.2f} < {tau})")
        else:
            s["support"] = None
        s["ok"] = not reasons
        s["reasons"] = reasons
    return sentences


def make_answer(query, lang, excerpts, backend, embed, tau=None):
    """Full pipeline for one question; excerpts come from select_excerpts. Returns a dict for the API."""
    t0 = time.time()
    system, user = prompt_for(query, excerpts, lang)
    raw = backend.complete(system, user)
    res = {"model": f"{backend.name}:{backend.model}", "raw": raw, "excerpts": [{k: e[k] for k in ("n", "title", "article_no", "heading")} for e in excerpts]}
    if NO_ANSWER.match(raw):
        res.update(status="abstain", sentences=[], seconds=round(time.time() - t0, 1))
        return res
    sentences = verify(split_answer(raw), excerpts, embed, lang, tau)
    kept = [s for s in sentences if s["ok"]]
    res.update(status="ok" if kept else "unverified", sentences=sentences, kept=len(kept), dropped=len(sentences) - len(kept), seconds=round(time.time() - t0, 1))
    return res


def select_excerpts(hits, query, texts_of, explain, budget=950, n=4):
    """The first n hits as numbered excerpts: the heading line plus the sentences closest to the question, in reading order, up to `budget` characters."""
    out = []
    for h in hits[:n]:
        text = texts_of(h)
        if not text:
            continue
        first = text.split(chr(10))[0].strip()
        spans = explain(query, text, 6)
        picked, used = [], len(first)
        for sp in sorted(spans, key=lambda s: -s["score"]):
            seg = text[sp["start"]:sp["end"]]
            if used + len(seg) + 1 <= budget:
                picked.append((sp["start"], seg))
                used += len(seg) + 1
        body = " ".join(seg for _, seg in sorted(picked)) if picked else text[:budget - len(first)]
        out.append({"n": len(out) + 1, "title": h.title, "article_no": h.article_no, "heading": h.heading, "text": f"{first}\n{body}".strip()})
    return out
