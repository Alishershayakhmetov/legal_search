"""Web demo without extra dependencies: a small HTTP server (Python standard library) plus one HTML page.

Run:  python app/server.py [--port 8610]      then open http://localhost:8610
Pre-filled links:  http://localhost:8610/?q=статья 1 конституции рк&mode=articles   (mode: articles | titles | compare)
"""
import argparse
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import ROOT, Filters, SearchEngine, log_feedback  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
METHODS = {"dense": "Смысловой (bge-m3)", "bm25": "По словам (BM25)", "hybrid": "Гибрид (смысл + слова)"}
FIRST_LINE = re.compile(r"^(Статья\s+\S+|\d+(?:-\d+)?\s*-\s*бап)[^\n]*\n", re.I)
MAX_BODY = 64 * 1024
LOCK = threading.Lock()  # one search at a time: the encoder and the GPU are shared
ENGINE = None


def make_filters(d):
    d = d or {}
    return Filters(only_in_force=bool(d.get("only_in_force", True)), hide_drafts=bool(d.get("hide_drafts", True)),
                   hide_amending=bool(d.get("hide_amending", True)), include_unlinked=bool(d.get("include_unlinked", True)),
                   kinds=tuple(d.get("kinds") or ()), year_from=int(d.get("year_from", 1990)), year_to=int(d.get("year_to", 2026)),
                   force_prior=float(d.get("force_prior", 0.0)))


def hit_to_dict(hit, lang):
    """Article card: the snippet is shown in the language of the question when that language is available."""
    show = "kk" if lang == "kk" and "kk" in hit.texts else "ru" if "ru" in hit.texts else next(iter(hit.texts), "ru")
    body = FIRST_LINE.sub("", hit.texts.get(show, ""), count=1)
    heading = hit.headings.get(show) or hit.heading
    return {"title": hit.title, "article_no": hit.article_no, "heading": "" if heading == "None" else heading, "kind": hit.kind,
            "year": hit.year, "in_force": hit.in_force, "url": hit.url, "methods": list(hit.methods),
            "snippet": body[:600] + ("…" if len(body) > 600 else ""), "texts": hit.texts}


def run_search(req):
    k = max(3, min(int(req.get("k", 8)), 20))
    filters = make_filters(req.get("filters"))
    query = str(req.get("query", "")).strip()
    mode = req.get("mode", "articles")
    if not query:
        return {"error": "empty query"}
    with LOCK:
        if mode == "titles":
            results, info = ENGINE.search_titles(query, k, filters)
            return {"mode": mode, "lang": info["lang"], "seconds": info["seconds"], "results": results}
        if mode == "compare":
            columns = []
            for method, label in METHODS.items():
                hits, info = ENGINE.search(query, min(k, 6), method, filters)
                columns.append({"label": label, "seconds": info["seconds"], "notes": info["notes"],
                                "hits": [{"title": h.title, "article_no": h.article_no, "heading": h.headings.get("kk" if info["lang"] == "kk" else "ru") or h.heading} for h in hits]})
            return {"mode": mode, "lang": info["lang"], "columns": columns}
        method = req.get("method", "dense")
        hits, info = ENGINE.search(query, k, method if method in METHODS else "dense", filters)
        return {"mode": "articles", "lang": info["lang"], "seconds": info["seconds"], "searched": info["searched"], "notes": info["notes"],
                "direct": info.get("direct", 0), "low_confidence": info.get("low_confidence", False), "hits": [hit_to_dict(h, info["lang"]) for h in hits]}


def examples():
    """Every query of the test set, per language (the needs that have judgments)."""
    try:
        needs = json.loads((ROOT / "annotation" / "needs.json").read_text(encoding="utf-8"))
        judged = set(json.loads((ROOT / "annotation" / "qrels_v1.json").read_text(encoding="utf-8")))
    except OSError:
        return {"ru": [], "kk": [], "en": []}
    return {lang: [n[lang] for n in needs if n["id"] in judged] for lang in ("ru", "kk", "en")}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # keep the console quiet
        pass

    def _send(self, status, body, content_type):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, obj, status=200):
        self._send(status, json.dumps(obj, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in ("/", "/index.html"):
            self._send(200, (STATIC / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif path == "/api/examples":
            self._json(examples())
        elif path == "/api/kinds":
            self._json(sorted(ENGINE.df.kind.dropna().unique().tolist()))
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY:
            return self._json({"error": "request too large"}, 413)
        try:
            req = json.loads(self.rfile.read(length) or b"{}")
            if self.path == "/api/search":
                return self._json(run_search(req))
            if self.path == "/api/feedback":
                ok = log_feedback(str(req.get("query", ""))[:500], "article", (str(req.get("title", ""))[:300], str(req.get("article_no", ""))[:20]),
                                  "up" if req.get("label") == "up" else "down", keep_query=bool(req.get("consent")))
                return self._json({"saved": ok})
        except (ValueError, TypeError, KeyError) as e:
            return self._json({"error": f"bad request: {e}"}, 400)
        except Exception as e:  # keep the server alive and tell the page what failed
            return self._json({"error": f"{type(e).__name__}: {e}"}, 500)
        self._send(404, b"not found", "text/plain")


def main():
    global ENGINE
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8610)
    ap.add_argument("--host", default="127.0.0.1", help="default: this computer only")
    args = ap.parse_args()
    print("Loading indexes and the bge-m3 encoder (about a minute the first time)...", flush=True)
    ENGINE = SearchEngine()
    _ = ENGINE.model
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"Ready: http://localhost:{args.port}   (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
