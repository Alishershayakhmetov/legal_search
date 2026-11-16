"""Search engine behind the demo: article search (dense, BM25, hybrid) and act search by title.

Pure helpers (language detection, filter mask, grouping) are separate from the heavy parts (model, embeddings,
indexes) so they can be tested without any data.
"""
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "app"
sys.path.insert(0, str(ROOT / "src"))

KK_LETTERS = set("әғқңөұүһ")
RRF_K = 60
MODEL_NAME = "BAAI/bge-m3"


# legal force of an act kind, used by the experimental prior (src/40_rank_experiments.py)
FORCE_LEVEL = {"Конституция": 5, "Конституционный закон": 4, "Кодекс": 3, "Закон": 2, "Указ": 1}


@dataclass(frozen=True)
class Filters:
    only_in_force: bool = True
    hide_drafts: bool = True
    hide_amending: bool = True
    include_unlinked: bool = True
    kinds: tuple = ()  # empty = every kind
    year_from: int = 1990
    year_to: int = 2026
    force_prior: float = 0.0  # experimental: bonus added to the semantic score by legal force of the act kind (see FORCE_LEVEL)


@dataclass
class Hit:
    title: str
    article_no: str
    heading: str
    section: str
    kind: str
    year: object
    in_force: object
    url: object
    law_id: object
    score: float
    matched_lang: str
    texts: dict = field(default_factory=dict)  # lang -> article text
    headings: dict = field(default_factory=dict)  # lang -> article heading
    methods: tuple = ()


def detect_language(text):
    """Script-based guess: Kazakh letters -> kk, mostly Latin -> en, otherwise ru."""
    low = text.lower()
    letters = [c for c in low if c.isalpha()]
    if not letters:
        return "ru"
    if any(c in KK_LETTERS for c in letters):
        return "kk"
    latin = sum("a" <= c <= "z" for c in letters)
    return "en" if latin / len(letters) > 0.6 else "ru"


# Top-1 cosine score of bge-m3 below which a question most likely has no answer in the corpus (src/41_robustness.py: the 5% quantile of the
# in-scope questions per language; every one of 20 clearly off-topic and 6 borderline questions per language scored below it).
CONFIDENCE_MIN = {"ru": 0.62, "kk": 0.61, "en": 0.58}
LOW_CONFIDENCE_NOTE = ("Надёжной статьи для этого вопроса не найдено: возможно, он не относится к законодательству РК или в базе нет подходящей нормы. "
                       "Результаты ниже могут быть случайными.")
EVASION = re.compile(
    r"как\s+(?:можно\s+)?(?:обойти|обмануть|скрыть|утаить|подделать|избежать\s+(?:уплаты|ответственности|наказания))|уклониться\s+от\s+(?:уплаты|налог)|как\s+не\s+платить\s+налог"
    r"|заңды\s+айналып\s+өт|салықтан\s+жалтар|жауапкершіліктен\s+құтыл|how\s+(?:to|can\s+i|do\s+i)\s+(?:evade|bypass|get\s+around|avoid\s+paying|hide\s+(?:my\s+)?income|forge)", re.I)
POLICY_NOTE = ("Система справочная: она показывает, что говорит закон, в том числе об ответственности, и не подсказывает способов обойти закон или избежать ответственности. "
               "При реальных затруднениях обратитесь к юристу.")


def policy_notice(query):
    """A short notice for questions that ask how to evade the law; the results are still the legal texts (liability articles)."""
    return POLICY_NOTE if EVASION.search(query) else None


# Router: a short query whose best act title is clearly closer than its best article is a request for an act, not a question (src/43_router_eval.py).
ROUTER_MARGIN = 0.0
ROUTER_MAX_WORDS = 7


def route_query(query, top_title_score, top_article_score):
    """'titles' when the query looks like the name of an act, otherwise 'articles'. Queries with an article number go to articles (exact lookup)."""
    if parse_reference(query) is not None:
        return "articles"
    short = len(query.split()) <= ROUTER_MAX_WORDS
    return "titles" if short and top_title_score - top_article_score >= ROUTER_MARGIN else "articles"


LAT_TO_CYR = {"shch": "щ", "zh": "ж", "kh": "х", "ts": "ц", "ch": "ч", "sh": "ш", "yu": "ю", "ya": "я", "yo": "ё", "a": "а", "b": "б", "v": "в", "g": "г", "d": "д",
              "e": "е", "z": "з", "i": "и", "y": "ы", "k": "к", "l": "л", "m": "м", "n": "н", "o": "о", "p": "п", "r": "р", "s": "с", "t": "т", "u": "у", "f": "ф",
              "h": "х", "c": "к", "j": "ж", "q": "к", "w": "в", "x": "кс"}
LAT_ORDER = sorted(LAT_TO_CYR, key=len, reverse=True)


def latin_to_cyrillic(text):
    """Back-transliterate a query typed with Latin letters ("kak vzyskat alimenty") into Russian letters; other characters stay."""
    low, out, i = text.lower(), [], 0
    while i < len(low):
        for key in LAT_ORDER:
            if low.startswith(key, i):
                out.append(LAT_TO_CYR[key])
                i += len(key)
                break
        else:
            out.append(low[i])
            i += 1
    return "".join(out)


MIN_TITLE_SCORE = 0.6  # cosine similarity between the act words of a query and an act title
ARTICLE_WORD = r"(?:стать\w+|ст\.?|бап\w*|баб\w*|article|art\.?)"
REF_BEFORE = re.compile(rf"(?<![\w-]){ARTICLE_WORD}\s*[№#]?\s*(\d+(?:-\d+)?)(?![\w-])", re.I)  # "статья 52", "ст. 52", "article 1"
REF_AFTER = re.compile(rf"(?<![\w-])(\d+(?:-\d+)?)\s*[-‑–]?\s*{ARTICLE_WORD}(?!\w)", re.I)  # "52 статья", "52-бап"
FILLER = {"в", "во", "по", "из", "согласно", "текст", "покажи", "про", "о", "об", "что", "какая", "такое", "рк", "республики", "республика", "казахстан",
          "қр", "қазақстан", "республикасының", "of", "the", "in", "kazakhstan", "republic", "and", "и", "к", "на", "для", "для"}
ABBREVIATIONS = {"тк": "Трудовой кодекс", "гк": "Гражданский кодекс", "ук": "Уголовный кодекс", "упк": "Уголовно-процессуальный кодекс",
                 "гпк": "Гражданский процессуальный кодекс", "нк": "Налоговый кодекс", "коап": "Кодекс об административных правонарушениях",
                 "зк": "Земельный кодекс", "ск": "Социальный кодекс", "пк": "Предпринимательский кодекс", "бк": "Бюджетный кодекс", "эк": "Экологический кодекс"}


# Upper-case abbreviations are spelled out before encoding ("ТК" -> "ТК (Трудовой кодекс Республики Казахстан)"): the encoder does not know them.
ABBREV_FULL = {"ТК": "Трудовой кодекс Республики Казахстан", "ГК": "Гражданский кодекс Республики Казахстан", "УК": "Уголовный кодекс Республики Казахстан",
               "УПК": "Уголовно-процессуальный кодекс Республики Казахстан", "ГПК": "Гражданский процессуальный кодекс Республики Казахстан",
               "НК": "Налоговый кодекс Республики Казахстан", "КоАП": "Кодекс об административных правонарушениях", "ЗК": "Земельный кодекс Республики Казахстан",
               "СК": "Социальный кодекс Республики Казахстан", "ПК": "Предпринимательский кодекс Республики Казахстан", "БК": "Бюджетный кодекс Республики Казахстан",
               "МРП": "месячный расчетный показатель", "МЗП": "минимальная заработная плата", "ИП": "индивидуальный предприниматель",
               "ТОО": "товарищество с ограниченной ответственностью", "АО": "акционерное общество", "БИН": "бизнес-идентификационный номер",
               "ИИН": "индивидуальный идентификационный номер", "НДС": "налог на добавленную стоимость", "ИПН": "индивидуальный подоходный налог",
               "КПН": "корпоративный подоходный налог", "ОСМС": "обязательное социальное медицинское страхование", "ЕНПФ": "единый накопительный пенсионный фонд",
               "ДТП": "дорожно-транспортное происшествие", "ЖКХ": "жилищно-коммунальное хозяйство", "ГУ": "государственное учреждение"}
ABBREV_RE = re.compile(r"(?<![\w-])(" + "|".join(sorted(ABBREV_FULL, key=len, reverse=True)) + r")(?![\w-])")


def expand_abbreviations(query):
    """Append the full name after each known abbreviation; other text is unchanged."""
    return ABBREV_RE.sub(lambda m: f"{m.group(1)} ({ABBREV_FULL[m.group(1)]})", query)


def parse_reference(query):
    """Split a query like 'статья 1 конституции РК' into (article number, words naming the act); None if it has no article number."""
    m = REF_BEFORE.search(query) or REF_AFTER.search(query)
    if not m:
        return None
    rest = (query[:m.start()] + " " + query[m.end():]).replace(",", " ").replace(".", " ")
    words = [w for w in rest.split() if w.lower() not in FILLER]
    if not words:
        return None
    return m.group(1), " ".join(ABBREVIATIONS.get(w.lower(), w) for w in words)


AMENDING = r"о внесении (?:изменени|дополнени)|өзгерістер(?: мен толықтырулар)? енгізу|толықтырулар енгізу"


def tidy_metadata(df, title_col):
    """Corrections applied when the tables are loaded: the Constitution has its own kind; acts whose title announces amendments
    are flagged wherever the phrase stands (titles like «Закон Республики Казахстан "О внесении изменений …"» were missed)."""
    low = df[title_col].fillna("").str.lower()
    df.loc[low.str.startswith("конституция республики казахстан"), "kind"] = "Конституция"
    df["is_amending"] = df.is_amending.fillna(False).astype(bool) | low.str.contains(AMENDING, regex=True)


def build_mask(df, f):
    """Boolean numpy mask over the rows of an articles-like table."""
    m = np.ones(len(df), dtype=bool)
    if f.only_in_force:
        m &= (df.is_repealed != 1).to_numpy()
    if not f.include_unlinked:
        m &= df.linked.to_numpy()
    if f.hide_drafts:
        m &= ~df.is_draft.to_numpy()
    if f.hide_amending:
        m &= ~df.is_amending.to_numpy()
    if f.kinds:
        m &= df.kind.isin(f.kinds).to_numpy()
    year = df.adopted_year
    m &= (year.isna() | ((year >= f.year_from) & (year <= f.year_to))).to_numpy()
    return m


def rrf(rankings, k=100):
    score = {}
    for lst in rankings:
        for r, d in enumerate(lst):
            score[d] = score.get(d, 0.0) + 1.0 / (RRF_K + r + 1)
    return sorted(score, key=score.get, reverse=True)[:k], score


def group_rows(df, rows, scores, twin_index, limit):
    """Collapse passages to distinct articles (an article exists in ru and kk): best row first, order kept."""
    seen, out = set(), []
    for r, s in zip(rows, scores):
        row = df.iloc[r]
        key = (row.family, row.article_no)
        if key in seen:
            continue
        seen.add(key)
        out.append((key, int(r), float(s)))
        if len(out) == limit:
            break
    return out


class SearchEngine:
    def __init__(self, data_dir=DATA, device=None):
        import torch
        self.torch = torch
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.df = pd.read_parquet(data_dir / "articles.parquet")
        self.acts = pd.read_parquet(data_dir / "acts.parquet").set_index("law_id")
        ids = np.load(ROOT / "data" / "index" / "emb_bge-m3_articles" / "doc_ids.npy")
        if len(ids) != len(self.df):
            raise RuntimeError("articles table and embeddings are out of step; rebuild with src/33_build_app_data.py")
        parts = sorted((ROOT / "data" / "index" / "emb_bge-m3_articles").glob("part_*.npy"))
        emb = np.concatenate([np.load(p) for p in parts])
        tidy_metadata(self.df, "display_title")
        tidy_metadata(self.acts, "title_ru")
        self.emb = torch.from_numpy(emb).to(self.device)
        if self.device == "cpu":
            self.emb = self.emb.float()
        self._force = self.torch.from_numpy(self.df.kind.map(FORCE_LEVEL).fillna(0).to_numpy(dtype=np.float32)).to(self.device)
        self._by_law = None
        self._model = None
        self._bm25 = {}
        self._masks = {}
        self._twins = None
        self._titles = None

    # -- models and indexes (loaded on first use) --------------------------------------------------------
    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            kw = {"torch_dtype": self.torch.float16} if self.device == "cuda" else {}
            self._model = SentenceTransformer(MODEL_NAME, device=self.device, model_kwargs=kw)
            self._model.max_seq_length = 384
        return self._model

    def bm25(self, lang):
        if lang not in self._bm25:
            from search_lib import Searcher
            mode = "stem" if lang == "ru" else "p5"
            self._bm25[lang] = Searcher.load(DATA / f"bm25_{lang}_{mode}.npz", lang, mode)
        return self._bm25[lang]

    def encode(self, text):
        q = self.model.encode([text], normalize_embeddings=True, convert_to_tensor=True)
        return q.to(self.emb.dtype)[0]

    def mask(self, f):
        if f not in self._masks:
            self._masks[f] = build_mask(self.df, f)
        return self._masks[f]

    @property
    def twins(self):
        if self._twins is None:
            idx = {}
            for i, (fam, art, lang) in enumerate(zip(self.df.family, self.df.article_no, self.df.lang)):
                idx.setdefault((fam, art), {}).setdefault(lang, []).append(i)
            self._twins = idx
        return self._twins

    @property
    def by_law(self):
        """(law_id, article number) -> rows of that article in every language."""
        if self._by_law is None:
            idx = {}
            for i, (lid, art) in enumerate(zip(self.df.law_id, self.df.article_no)):
                if isinstance(lid, str):
                    idx.setdefault((lid, art), []).append(i)
            self._by_law = idx
        return self._by_law

    def lookup_reference(self, query, filters=Filters()):
        """'статья 1 конституции РК', 'ст. 52 ТК', '52-бап' -> that article of the act the words name (exact lookup, no ranking)."""
        ref = parse_reference(query)
        if not ref:
            return []
        article_no, act_text = ref
        acts, _ = self.search_titles(act_text + " Республики Казахстан", 6, Filters(only_in_force=filters.only_in_force, hide_drafts=True, hide_amending=True))
        hits = []
        for a in acts:
            if a["score"] < MIN_TITLE_SCORE:
                break
            rows = self.by_law.get((a["law_id"], article_no))
            if rows:
                key = (self.df.family.iloc[rows[0]], article_no)
                hits.append(self._hit(key, rows[0], 1.0, ("номер статьи",)))
            if len(hits) == 2:
                break
        return hits

    # -- article search ----------------------------------------------------------------------------------
    def _dense_rows(self, query, mask, k, prior=0.0):
        scores = (self.emb @ self.encode(query)).float()
        if prior:
            scores = scores + prior * self._force
        scores = scores.masked_fill(~self.torch.from_numpy(mask).to(self.device), -1e4)
        top = self.torch.topk(scores, k)
        return top.indices.cpu().numpy(), top.values.cpu().numpy()

    def _bm25_rows(self, query, lang, mask, k):
        s = self.bm25(lang)
        rows, scores = s.search(query, 2000)
        keep = mask[rows]
        return rows[keep][:k], scores[keep][:k]

    def search(self, query, k=10, method="dense", filters=Filters()):
        """Return (hits, info). method: dense | bm25 | hybrid."""
        t0 = time.time()
        lang = detect_language(query)
        mask = self.mask(filters)
        pool = max(60, k * 6)
        qx = expand_abbreviations(query)
        notes = []
        low_confidence = False
        rankings = {}
        if method in ("dense", "hybrid"):
            rows, sc = self._dense_rows(qx, mask, pool, filters.force_prior)
            if lang == "en":  # a question typed in Latin letters may be Russian ("kak vzyskat alimenty"): keep the reading the model is surer about
                alt = latin_to_cyrillic(query)
                r2, s2 = self._dense_rows(alt, mask, pool, filters.force_prior)
                if s2[0] > sc[0]:
                    rows, sc, query, qx, lang = r2, s2, alt, expand_abbreviations(alt), "ru"
                    notes.append(f"Запрос набран латиницей и прочитан как русский: «{alt}».")
            rankings["dense"] = (list(rows), list(sc))
            top1 = float(sc[0]) - filters.force_prior * float(self._force[int(rows[0])]) if len(rows) else 0.0
            if top1 < CONFIDENCE_MIN.get(lang, 0.0):
                low_confidence = True
                notes.append(LOW_CONFIDENCE_NOTE)
        policy = policy_notice(query)
        if policy:
            notes.append(policy)
        if method in ("bm25", "hybrid"):
            if lang == "en":
                notes.append("BM25 ищет по словам и не работает с английским текстом: для английского запроса используется только смысловой поиск.")
                if method == "bm25":
                    return [], {"lang": lang, "notes": notes, "seconds": time.time() - t0, "searched": int(mask.sum())}
            else:
                rows, sc = self._bm25_rows(qx, lang, mask, pool)
                rankings["bm25"] = (list(rows), list(sc))
        if len(rankings) == 1:
            (name, (rows, sc)), = rankings.items()
            order, scores = rows, sc
            methods = {r: (name,) for r in rows}
        else:
            order, fused = rrf([r for r, _ in rankings.values()], pool)
            scores = [fused[r] for r in order]
            methods = {r: tuple(n for n, (rr, _) in rankings.items() if r in rr) for r in order}
        grouped = group_rows(self.df, order, scores, self.twins, k)
        hits = [self._hit(key, row, score, methods.get(row, ())) for key, row, score in grouped]
        direct = self.lookup_reference(query, filters)
        if direct:
            seen = {(h.title, h.article_no) for h in direct}
            hits = (direct + [h for h in hits if (h.title, h.article_no) not in seen])[:k]
        return hits, {"lang": lang, "notes": notes, "seconds": time.time() - t0, "searched": int(mask.sum()), "direct": len(direct), "low_confidence": low_confidence}

    def _hit(self, key, row, score, methods):
        r = self.df.iloc[row]
        if "_text_col" not in self.__dict__:  # plain arrays: iloc on the whole frame copied every column for each twin (0.3 s per hit)
            self._text_col, self._head_col = self.df["text"].to_numpy(), self.df["heading"].to_numpy()
        texts, headings = {}, {}
        for lg, idxs in self.twins.get(key, {}).items():
            texts[lg] = chr(10).join(self._text_col[i] for i in idxs)
            headings[lg] = str(self._head_col[idxs[0]] or "")
        ru_head = headings.get("ru") or str(r.heading or "")
        return Hit(title=str(r.display_title), article_no=str(r.article_no), heading=ru_head, section=str(r.section or ""), headings=headings,
                   kind=str(r.kind), year=None if pd.isna(r.adopted_year) else int(r.adopted_year),
                   in_force=None if pd.isna(r.is_repealed) else not bool(r.is_repealed),
                   url=None if pd.isna(r.adilet_url) else r.adilet_url, law_id=None if pd.isna(r.law_id) else r.law_id,
                   score=score, matched_lang=str(r.lang), texts=texts, methods=tuple(methods))

    def explain(self, query, text, k=3):
        """The k sentences of an article closest to the query: [{'start', 'end', 'score'}] in reading order."""
        spans = split_sentences(text)
        if not spans:
            return []
        sentences = [text[a:b] for a, b in spans]
        emb = self.model.encode(sentences, batch_size=32, normalize_embeddings=True, convert_to_tensor=True).to(self.emb.dtype)
        scores = (emb @ self.encode(expand_abbreviations(query))).float().cpu().numpy()
        top = sorted(scores.argsort()[::-1][:k])
        return [{"start": spans[i][0], "end": spans[i][1], "score": round(float(scores[i]), 3)} for i in top]

    # -- machine translation of a snippet (English users otherwise get Russian or Kazakh text) ---------------------------
    NLLB = "facebook/nllb-200-distilled-600M"
    NLLB_CODE = {"ru": "rus_Cyrl", "kk": "kaz_Cyrl", "en": "eng_Latn"}

    def translate(self, text, src, tgt, max_chars=1400):
        """Unofficial machine translation (NLLB-200 600M) of the start of a text; cached. Long texts are cut at a sentence boundary."""
        key = (hashlib.md5(text.encode("utf-8")).hexdigest(), src, tgt)
        cache = self.__dict__.setdefault("_tr_cache", {})
        if key in cache:
            return cache[key]
        if "_nllb" not in self.__dict__:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            self._nllb_tok = AutoTokenizer.from_pretrained(self.NLLB)
            m = AutoModelForSeq2SeqLM.from_pretrained(self.NLLB, torch_dtype=self.torch.float16 if self.device == "cuda" else self.torch.float32)
            self._nllb = m.to(self.device).eval()
        piece = text[:max_chars]
        if len(text) > max_chars:
            cut = max(piece.rfind(". "), piece.rfind(chr(10)))
            piece = piece[:cut + 1] if cut > 200 else piece
        sentences = [s.strip() for s in re.split(r"(?<=[.;:])\s+|" + chr(10) + "+", piece) if s.strip()]
        merged = []
        for s in sentences:  # a bare list number such as "1." is glued to the sentence after it
            if merged and re.fullmatch(r"[\d.()\s-]{1,6}", merged[-1]):
                merged[-1] += " " + s
            else:
                merged.append(s)
        sentences = merged
        tok = self._nllb_tok
        tok.src_lang = self.NLLB_CODE[src]
        out = []
        for i in range(0, len(sentences), 8):
            enc = tok(sentences[i:i + 8], return_tensors="pt", padding=True, truncation=True, max_length=200).to(self.device)
            with self.torch.no_grad():
                gen = self._nllb.generate(**enc, forced_bos_token_id=tok.convert_tokens_to_ids(self.NLLB_CODE[tgt]), num_beams=3, max_new_tokens=220)
            out += tok.batch_decode(gen, skip_special_tokens=True)
        result = {"text": " ".join(out), "cut": len(piece) < len(text)}
        cache[key] = result
        return result

    # -- act search by title -----------------------------------------------------------------------------
    def _load_titles(self):
        if self._titles is None:
            t = pd.read_parquet(DATA / "titles.parquet")
            parts = sorted((DATA / "title_emb").glob("part_*.npy"))
            emb = self.torch.from_numpy(np.concatenate([np.load(p) for p in parts])).to(self.device)
            if self.device == "cpu":
                emb = emb.float()
            if len(emb) != len(t):
                raise RuntimeError("title embeddings are incomplete; run src/34_embed_titles.py")
            self._titles = (t, emb)
        return self._titles

    def route(self, query):
        """Decide between 'titles' (find an act by name) and 'articles' (find an article for a question); see route_query."""
        t, _ = self.search_titles(query, 1, Filters())
        _, a = self._dense_rows(expand_abbreviations(query), self.mask(Filters()), 1)
        return route_query(query, t[0]["score"] if t else 0.0, float(a[0]))

    def search_titles(self, query, k=10, filters=Filters()):
        t0 = time.time()
        titles, emb = self._load_titles()
        scores = (emb @ self.encode(query)).float()
        top = self.torch.topk(scores, min(len(scores), 400))
        idx, val = top.indices.cpu().numpy(), top.values.cpu().numpy()
        out, seen = [], set()
        for i, s in zip(idx, val):
            lid = titles.law_id.iloc[i]
            if lid in seen or lid not in self.acts.index:
                continue
            a = self.acts.loc[lid]
            if filters.only_in_force and a.is_repealed == 1:
                continue
            if filters.hide_drafts and a.is_draft:
                continue
            if filters.hide_amending and a.is_amending:
                continue
            if filters.kinds and a.kind not in filters.kinds:
                continue
            seen.add(lid)
            out.append({"law_id": lid, "title": a.title_ru if isinstance(a.title_ru, str) else titles.title.iloc[i], "title_kk": a.title_kk,
                        "kind": a.kind, "year": None if pd.isna(a.adopted_year) else int(a.adopted_year), "in_force": not bool(a.is_repealed),
                        "url": a.adilet_url, "score": float(s)})
            if len(out) == k:
                break
        return out, {"lang": detect_language(query), "seconds": time.time() - t0}


NOTE_LINE = re.compile(r"^(Сноска|Ескерту|Примечание ИЗПИ|ЗҚАИ)")


def split_sentences(text, min_chars=20):
    """[(start, end)] character spans of the sentences of an article, without the heading line and without footnotes."""
    spans, pos = [], 0
    for li, line in enumerate(text.split(chr(10))):
        start = pos
        pos += len(line) + 1
        if li == 0 or NOTE_LINE.match(line.strip()):
            continue
        for m in re.finditer(r"[^.;:]+(?:[.;:]+|$)", line):
            s = m.group(0)
            lead = len(s) - len(s.lstrip())
            if len(s.strip()) >= min_chars:
                spans.append((start + m.start() + lead, start + m.end() - (len(s) - len(s.rstrip()))))
    return spans


def group_by_act(hits, limit=5):
    """One row per act, in the order of its best article: [(best hit, number of other articles of the same act among the hits)]."""
    order, rest = [], {}
    for h in hits:
        if h.title not in rest:
            rest[h.title] = [h, 0]
            order.append(h.title)
        else:
            rest[h.title][1] += 1
    return [tuple(rest[t]) for t in order[:limit]]


def log_feedback(query, kind, key, label, path=DATA / "feedback.jsonl", keep_query=False):
    """Append one thumbs-up/down judgment (extra relevance data). The question text is stored only when the user agreed
    (keep_query); otherwise only a short hash and the language are kept, which is enough to count but not to read."""
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "kind": kind, "key": list(key), "label": label, "lang": detect_language(query)}
    if keep_query:
        rec["query"] = query
    else:
        rec["query_hash"] = hashlib.sha1(query.encode("utf-8")).hexdigest()[:12]
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + chr(10))
        return True
    except OSError:
        return False
