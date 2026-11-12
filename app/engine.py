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


@dataclass(frozen=True)
class Filters:
    only_in_force: bool = True
    hide_drafts: bool = True
    hide_amending: bool = True
    include_unlinked: bool = True
    kinds: tuple = ()  # empty = every kind
    year_from: int = 1990
    year_to: int = 2026


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


MIN_TITLE_SCORE = 0.6  # cosine similarity between the act words of a query and an act title
ARTICLE_WORD = r"(?:стать\w+|ст\.?|бап\w*|баб\w*|article|art\.?)"
REF_BEFORE = re.compile(rf"(?<![\w-]){ARTICLE_WORD}\s*[№#]?\s*(\d+(?:-\d+)?)(?![\w-])", re.I)  # "статья 52", "ст. 52", "article 1"
REF_AFTER = re.compile(rf"(?<![\w-])(\d+(?:-\d+)?)\s*[-‑–]?\s*{ARTICLE_WORD}(?!\w)", re.I)  # "52 статья", "52-бап"
FILLER = {"в", "во", "по", "из", "согласно", "текст", "покажи", "про", "о", "об", "что", "какая", "такое", "рк", "республики", "республика", "казахстан",
          "қр", "қазақстан", "республикасының", "of", "the", "in", "kazakhstan", "republic", "and", "и", "к", "на", "для", "для"}
ABBREVIATIONS = {"тк": "Трудовой кодекс", "гк": "Гражданский кодекс", "ук": "Уголовный кодекс", "упк": "Уголовно-процессуальный кодекс",
                 "гпк": "Гражданский процессуальный кодекс", "нк": "Налоговый кодекс", "коап": "Кодекс об административных правонарушениях",
                 "зк": "Земельный кодекс", "ск": "Социальный кодекс", "пк": "Предпринимательский кодекс", "бк": "Бюджетный кодекс", "эк": "Экологический кодекс"}


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
        extra_dir = data_dir / "extra_emb"
        if (data_dir / "extra_articles.parquet").exists() and (extra_dir / "DONE").exists():
            # articles missed by the first chunking run (headings without a period, e.g. the Constitution)
            extra = pd.read_parquet(data_dir / "extra_articles.parquet")
            extra_emb = np.concatenate([np.load(p) for p in sorted(extra_dir.glob("part_*.npy"))])
            if len(extra) != len(extra_emb):
                raise RuntimeError("supplement table and embeddings are out of step; run src/37_embed_extra.py")
            self.df = pd.concat([self.df, extra], ignore_index=True)
            emb = np.concatenate([emb, extra_emb])
        tidy_metadata(self.df, "display_title")
        tidy_metadata(self.acts, "title_ru")
        self.emb = torch.from_numpy(emb).to(self.device)
        if self.device == "cpu":
            self.emb = self.emb.float()
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
    def _dense_rows(self, query, mask, k):
        scores = self.emb @ self.encode(query)
        scores = scores.float().masked_fill(~self.torch.from_numpy(mask).to(self.device), -1e4)
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
        notes = []
        rankings = {}
        if method in ("dense", "hybrid"):
            rows, sc = self._dense_rows(query, mask, pool)
            rankings["dense"] = (list(rows), list(sc))
        if method in ("bm25", "hybrid"):
            if lang == "en":
                notes.append("BM25 ищет по словам и не работает с английским текстом: для английского запроса используется только смысловой поиск.")
                if method == "bm25":
                    return [], {"lang": lang, "notes": notes, "seconds": time.time() - t0, "searched": int(mask.sum())}
            else:
                rows, sc = self._bm25_rows(query, lang, mask, pool)
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
        return hits, {"lang": lang, "notes": notes, "seconds": time.time() - t0, "searched": int(mask.sum()), "direct": len(direct)}

    def _hit(self, key, row, score, methods):
        r = self.df.iloc[row]
        texts = {}
        for lg, idxs in self.twins.get(key, {}).items():
            sub = self.df.iloc[idxs]
            texts[lg] = "\n".join(sub.text)
        headings = {lg: str(self.df.iloc[idxs[0]].heading or "") for lg, idxs in self.twins.get(key, {}).items()}
        ru_head = headings.get("ru") or str(r.heading or "")
        return Hit(title=str(r.display_title), article_no=str(r.article_no), heading=ru_head, section=str(r.section or ""), headings=headings,
                   kind=str(r.kind), year=None if pd.isna(r.adopted_year) else int(r.adopted_year),
                   in_force=None if pd.isna(r.is_repealed) else not bool(r.is_repealed),
                   url=None if pd.isna(r.adilet_url) else r.adilet_url, law_id=None if pd.isna(r.law_id) else r.law_id,
                   score=score, matched_lang=str(r.lang), texts=texts, methods=tuple(methods))

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
