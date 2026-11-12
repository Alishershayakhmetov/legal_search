"""Sparse retrieval over hashed term counts: keyword overlap, TF-IDF cosine and BM25.

One index is built per (language, analyzer, scope). The count matrix is documents x 2**23 hashed terms;
weights are precomputed per cell and stored column-wise so a query touches only its own posting lists.
"""
import time
from functools import partial
from pathlib import Path

import numpy as np
import scipy.sparse as sp
from joblib import Parallel, delayed
from sklearn.feature_extraction.text import HashingVectorizer

from textproc import analyze

ROOT = Path(__file__).resolve().parent.parent
INDEX_DIR = ROOT / "data" / "index"
N_FEATURES = 2**23
K1, B = 1.2, 0.75


def make_vectorizer(lang, mode):
    return HashingVectorizer(analyzer=partial(analyze, lang=lang, mode=mode), n_features=N_FEATURES,
                             alternate_sign=False, norm=None, dtype=np.float32)


def count_matrix(texts, lang, mode, n_jobs=14, chunk=20_000):
    hv = make_vectorizer(lang, mode)
    parts = Parallel(n_jobs=n_jobs)(delayed(hv.transform)(texts[i:i + chunk]) for i in range(0, len(texts), chunk))
    return sp.vstack(parts, format="csr")


def doc_frequency(C):
    return np.bincount(C.indices, minlength=C.shape[1])


def idf_vector(C):
    n = C.shape[0]
    df = doc_frequency(C)
    return np.log(1 + (n - df + 0.5) / (df + 0.5)).astype(np.float32)


def weights(C, scheme):
    """Return a CSC matrix of per-cell weights for the chosen scheme."""
    n = C.shape[0]
    dl = np.asarray(C.sum(axis=1)).ravel()
    rows = np.repeat(np.arange(n), np.diff(C.indptr))
    tf = C.data
    if scheme == "bm25":
        idf = idf_vector(C)
        w = idf[C.indices] * tf * (K1 + 1) / (tf + K1 * (1 - B + B * dl[rows] / dl.mean()))
    elif scheme == "tfidf":
        idf = idf_vector(C)
        w = (1 + np.log(tf)) * idf[C.indices]
        norms = np.sqrt(np.bincount(rows, weights=w.astype(np.float64) ** 2, minlength=n))
        w = w / np.maximum(norms[rows], 1e-9)
    elif scheme == "overlap":
        w = 1.0 - dl[rows] / 1e6  # every matched query term counts 1; shorter documents win ties
    else:
        raise ValueError(scheme)
    return sp.csr_matrix((w.astype(np.float32), C.indices, C.indptr), shape=C.shape).tocsc()


class Searcher:
    def __init__(self, W, doc_ids, lang, mode, scheme, idf=None):
        self.indptr, self.indices, self.data = W.indptr, W.indices, W.data
        self.doc_ids = doc_ids
        self.n = W.shape[0]
        self.lang, self.mode, self.scheme, self.idf = lang, mode, scheme, idf
        self.hv = make_vectorizer(lang, mode)

    def query_terms(self, text):
        return np.unique(self.hv.transform([text]).indices)

    def search(self, text, k=100):
        terms = self.query_terms(text)
        scores = np.zeros(self.n, dtype=np.float32)
        for t in terms:
            a, b = self.indptr[t], self.indptr[t + 1]
            scores[self.indices[a:b]] += self.data[a:b] * (self.idf[t] if self.scheme == "tfidf" else 1.0)
        if not len(terms) or scores.max() <= 0:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
        top = np.argpartition(-scores, min(k, self.n - 1))[:k]
        top = top[np.argsort(-scores[top])]
        top = top[scores[top] > 0]
        return self.doc_ids[top], scores[top]

    def save(self, path):
        np.savez(path, indptr=self.indptr, indices=self.indices, data=self.data, doc_ids=self.doc_ids)

    @classmethod
    def load(cls, path, lang, mode, scheme="bm25"):
        z = np.load(path)
        shape = (len(z["doc_ids"]), N_FEATURES)
        W = sp.csc_matrix((z["data"], z["indices"], z["indptr"]), shape=shape)
        return cls(W, z["doc_ids"], lang, mode, scheme)

    def size_mb(self):
        return (self.indptr.nbytes + self.indices.nbytes + self.data.nbytes) / 1e6


def build_searchers(texts, doc_ids, lang, mode, schemes=("bm25", "tfidf", "overlap"), log=print):
    t0 = time.time()
    C = count_matrix(texts, lang, mode)
    log(f"  counts {lang}/{mode}: {C.shape[0]:,} docs, {C.nnz / 1e6:.0f}M nonzeros, {time.time() - t0:.0f}s")
    idf = idf_vector(C)
    out = {}
    for sch in schemes:
        t1 = time.time()
        out[sch] = Searcher(weights(C, sch), doc_ids, lang, mode, sch, idf=idf)
        log(f"  weights {sch}: {out[sch].size_mb():.0f} MB, {time.time() - t1:.0f}s")
    return out
