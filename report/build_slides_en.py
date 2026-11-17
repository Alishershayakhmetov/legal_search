"""English defense presentation (pptx) built from the result files; speaker notes included."""
import glob
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "report" / "figures_en"
OLD = ROOT / "report" / "figures"
OUT = ROOT / "report" / "Presentation_Kazakh_Legal_Search_Engine.pptx"
NAVY, BLUE, GREY, LIGHT, ACCENT, GREEN = RGBColor(0x1F, 0x2A, 0x44), RGBColor(0x08, 0x51, 0x9C), RGBColor(0x59, 0x59, 0x59), RGBColor(0xEE, 0xF3, 0xFA), RGBColor(0xC0, 0x39, 0x2B), RGBColor(0x2E, 0x7D, 0x32)
FONT = "Calibri"


def load(pattern):
    rows = []
    for p in sorted(glob.glob(str(ROOT / "outputs" / pattern))):
        rows += json.loads(Path(p).read_text(encoding="utf-8"))
    return rows


def jload(name):
    return json.loads((ROOT / "outputs" / name).read_text(encoding="utf-8"))


SPARSE, DENSE = load("sparse_results_articles_rukk_wordp5stem_v1_c2.json"), load("dense_results_*_articles_v1_c2.json")
SIG, RANK, ROB, ANS, AUD = jload("significance.json"), jload("rank_experiments.json"), jload("robustness.json"), jload("answer_eval.json"), jload("answer_audit.json")["items"]


def g(rows, **kw):
    return next(r for r in rows if all(r.get(k) == v for k, v in kw.items()))


def f2(x):
    return f"{x:.2f}"


def f3(x):
    return f"{x:.3f}"


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def textbox(slide, x, y, w, h, text, size=18, bold=False, color=NAVY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    for i, line in enumerate(text if isinstance(text, list) else [text]):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        r = para.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.italic, r.font.name = Pt(size), bold, italic, FONT
        r.font.color.rgb = color
    return tb


def bullets(slide, x, y, w, h, items, size=18, gap=8):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.space_after = Pt(gap)
        bold_part, _, rest = it.partition("|")
        runs = []
        if rest:
            r1 = para.add_run(); r1.text = "• " + bold_part; r1.font.bold = True
            r2 = para.add_run(); r2.text = rest
            runs = [r1, r2]
        else:
            r1 = para.add_run(); r1.text = "• " + it
            runs = [r1]
        for r in runs:
            r.font.size, r.font.name = Pt(size), FONT
            r.font.color.rgb = NAVY
    return tb


def new_slide(title, subtitle=None, notes=""):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.12))
    bar.fill.solid(); bar.fill.fore_color.rgb = BLUE; bar.line.fill.background()
    textbox(s, 0.6, 0.35, 12.1, 0.8, title, size=30, bold=True)
    if subtitle:
        textbox(s, 0.6, 1.08, 12.1, 0.5, subtitle, size=16, color=GREY)
    s.notes_slide.notes_text_frame.text = notes
    textbox(s, 12.2, 7.05, 0.8, 0.3, str(len(prs.slides)), size=11, color=GREY, align=PP_ALIGN.RIGHT)
    return s


def table(slide, x, y, w, rows, col_w, size=13, header=True, row_h=0.38):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shape.table
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = ""
            run = cell.text_frame.paragraphs[0].add_run()
            run.text = str(val)
            run.font.size, run.font.name = Pt(size), FONT
            run.font.bold = header and ri == 0
            run.font.color.rgb = RGBColor(255, 255, 255) if header and ri == 0 else NAVY
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.fill.solid()
            cell.fill.fore_color.rgb = BLUE if header and ri == 0 else (LIGHT if ri % 2 == 0 else RGBColor(255, 255, 255))
        tbl.rows[ri].height = Inches(row_h)
    return tbl


def stat(slide, x, y, w, number, caption, color=BLUE):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(1.45))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
    textbox(slide, x, y + 0.1, w, 0.7, number, size=34, bold=True, color=color, align=PP_ALIGN.CENTER)
    textbox(slide, x + 0.1, y + 0.85, w - 0.2, 0.55, caption.split(chr(10)), size=13, color=GREY, align=PP_ALIGN.CENTER)


b_ru, b_kk, b_en = (g(DENSE, model="bge-m3", lang="ru", system="dense"), g(DENSE, model="bge-m3", lang="kk", system="dense"), g(DENSE, model="bge-m3", lang="en", system="dense_cross"))
bm_ru, bm_kk = g(SPARSE, lang="ru", analyzer="stem", scheme="bm25"), g(SPARSE, lang="kk", analyzer="p5", scheme="bm25")
rv = {(r["lang"], r["variant"]): r for r in RANK["summary"]}
RB = {(r["mode"], r["lang"], r["variant"]): r for r in ROB["summary"]}

# 1 title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
textbox(s, 0.9, 1.3, 11.5, 2.3, ["Kazakh Legal Search Engine", "Finding articles of Kazakhstani law by everyday questions"], size=40, bold=True, color=RGBColor(255, 255, 255))
textbox(s, 0.9, 3.9, 11.5, 0.6, "Topic 16 · queries in Kazakh, Russian and English · BM25 vs TF-IDF vs embeddings", size=20, color=RGBColor(0xBD, 0xD7, 0xEE))
textbox(s, 0.9, 5.3, 11.5, 1.2, ["Alisher Shayakhmetov · Arsen Zhambekov · Yernar Sakenov — group AAI-2604", "Programming for Data Analysis and Database · Applied AI (MSc) · Astana, November 2026"], size=16, color=RGBColor(0xBD, 0xD7, 0xEE))
s.notes_slide.notes_text_frame.text = "Topic 16 of the course list. I will show the data work, the methods we compared, the results with their uncertainty, and a short demo of the application."

# 2 problem
s = new_slide("The problem and what we extended", "The assigned task is title search; we answer questions",
              "The assigned task is to retrieve acts for a Kazakh query and compare BM25, TF-IDF and embeddings by Recall@k and MRR on at least fifty annotated queries. The source data are metadata only, so a user who describes a situation cannot find the law. "
              "We therefore linked a second source with full texts, search articles, and support Kazakh, Russian and English questions although there is no English text.")
bullets(s, 0.6, 1.8, 12.1, 4.5, [
    "Assigned (topic 16)|: retrieve legal acts for a Kazakh query; BM25 vs TF-IDF vs embeddings; Recall@k, MRR; at least 50 annotated queries.",
    "Why it is not enough|: the metadata hold titles, kinds, bodies and dates; “my employer has not paid my salary for two months” matches no title.",
    "Our extension|: (1) three query languages, (2) article-level search over full texts from a second source, (3) honest evaluation with intervals and significance tests.",
    "Hard parts|: everyday vs legal vocabulary; agglutinative Kazakh; many near-identical texts (bills, editions); truncated, ambiguous act titles.",
], size=19, gap=14)

# 3 data
s = new_slide("Data: three sources, 7.1 GB of text", "Metadata + full texts + a link to the official site",
              "The metadata file has 223 thousand acts. The Mendeley dataset provides the texts of current legislation as of April 2024 in Russian and Kazakh, licensed CC BY 4.0. The official site renders pages with JavaScript and disallows its API, so we only link to it.")
stat(s, 0.6, 1.9, 2.9, "223,245", "acts in the metadata\n(952 MB CSV → 30 MB Parquet)")
stat(s, 3.8, 1.9, 2.9, "204k", "text files\n(102,596 ru + 101,304 kk)")
stat(s, 7.0, 1.9, 2.9, "3.12 M", "passages after chunking\n(319,377 are articles)")
stat(s, 10.2, 1.9, 2.5, "0", "duplicate law_id;\n34.5% acts repealed")
table(s, 0.6, 3.8, 12.1, [["Source", "Content", "Licence", "Role"],
                          ["KazakhLawCorpus (Hugging Face)", "titles ru/kk, kind, body, dates, status", "Apache 2.0", "one record per act"],
                          ["Textual Foundations of Justice (Mendeley)", "full texts, as of 01.04.2024", "CC BY 4.0", "article text"],
                          ["adilet.zan.kz", "official database (JavaScript, API closed)", "—", "link-out only"]], [3.9, 4.2, 1.8, 2.2], size=14, row_h=0.55)

# 4 audit + SQL
s = new_slide("Audit, relational schema and SQL", "13 tables in third normal form, 13 analytic queries",
              "The audit found empty Kazakh titles, CAPTCHA text in titles, multi-valued fields, a mostly empty publication date and mixed-language reference fields. We normalised the schema with many-to-many tables and wrote thirteen queries with CTEs, window functions and subqueries; results are loaded into pandas.")
s.shapes.add_picture(str(ROOT / "docs" / "er_diagram.png"), Inches(0.5), Inches(1.7), height=Inches(5.0))
bullets(s, 7.0, 1.8, 5.8, 5.0, [
    "Audit|: 3.3% Kazakh titles empty, 57 are CAPTCHA text; publication date missing for 89%; 43–76% multi-valued fields.",
    "SQL|: CTE, LAG, RANK, ROW_NUMBER, SUM/AVG OVER, HAVING, subqueries.",
    "Findings|: 59.9% of current acts have text vs 4.5% of repealed; 40% of acts share a title with another act.",
], size=16, gap=10)

# 5 linking
s = new_slide("The hardest part: linking a file to an act", "File names have no id and titles are cut at 200 characters",
              "Texts are named by title, status label, kind, body and date. We link by the normalised title, then date and registry number, then body and region. A bug in the first version dropped short titles such as the Labour Code, so the main codes had no text; we found it while preparing the test set and fixed it.")
table(s, 0.6, 1.9, 7.4, [["", "Russian", "Kazakh"], ["Files", "102,596", "101,304"], ["Linked to one act", "79.8%", "81.1%"], ["Distinct acts with text", "80,916", "78,250"],
                         ["Date in name = adoption date", "96.8%", "98.7%"]], [3.8, 1.8, 1.8], size=15, row_h=0.55)
bullets(s, 8.4, 1.9, 4.5, 4.6, [
    "Bug found|: titles under five words (“Трудовой кодекс…”) did not match; 2,392 Russian files had no act.",
    "Fix|: accept a short title only if a status label follows; 120 unmatched left.",
    "Lesson|: check the data before the model.",
], size=16, gap=12)

# 6 chunking
s = new_slide("From text to searchable passages", "Articles first, then sentence-aware chunks",
              "Acts with article headings are cut into articles, long articles into passages of at most fifteen hundred characters with overlap. Tables of digits are dropped and exact duplicates are removed, keeping the copy that belongs to a real act. After fixing headings without a full stop the whole pipeline was re-run: 319,377 article passages.")
s.shapes.add_picture(str(FIG / "fig_pipeline.png"), Inches(0.6), Inches(1.7), width=Inches(12.1))
table(s, 0.6, 4.4, 12.1, [["", "Russian", "Kazakh"], ["Passages", "1,628,856", "1,495,552"], ["Article / other / table", "10.9% / 49.5% / 39.6%", "11.1% / 49.7% / 39.1%"],
                          ["In search indexes (no tables, no duplicates)", "888,356", "840,322"]], [5.6, 3.3, 3.2], size=14, row_h=0.5)

# 7 test set
s = new_slide("How we measure", "53 needs × 3 languages = 159 queries; 376 judged articles",
              "Each need is a real situation or concept question written in three languages. Judgments are per act and article; versions of one act are merged by comparing text hashes. We report Success at k, Recall at fifty, MRR and nDCG with bootstrap intervals and paired tests. The judgments were prepared by the author with an AI assistant and not reviewed independently.")
bullets(s, 0.6, 1.8, 7.0, 4.8, [
    "Needs|: 30 situations, 15 concept questions, 8 act titles; 19 topics.",
    "Judgments|: v1 = 67 answers, 100 related, 209 rejected (pooled from 8 system runs).",
    "Metrics|: Success@k, Recall@50, MRR@10, nDCG@10; 95% bootstrap CI; paired bootstrap and sign test.",
    "No training|: all models are used as published, so no train/test leakage; thresholds added later are flagged.",
], size=17, gap=12)
textbox(s, 8.0, 1.9, 4.7, 0.5, "Honest caveats", size=22, bold=True, color=ACCENT)
bullets(s, 8.0, 2.5, 4.7, 4.0, ["Drafted with an AI assistant, annotated in the team (Y. Sakenov); no lawyer review.", "Kazakh queries reviewed by the team; no objections.", "52 of 67 answers are code articles.", "45 needs per language: wide intervals."], size=16, gap=8)

# 8 methods
s = new_slide("What we compared", "Baseline → words (BM25) → meaning (embeddings) → hybrid",
              "The baseline counts matched words. TF-IDF and BM25 use a hashed sparse index. For Kazakh we compared word forms, a five-letter prefix and a suffix stemmer; for Russian Snowball. Dense retrieval uses three multilingual encoders. English queries go directly across languages or through translation.")
table(s, 0.6, 1.9, 12.1, [["Family", "Variants"], ["Baseline", "keyword overlap"], ["Lexical", "TF-IDF, BM25; word forms / 5-letter prefix / stemming; character n-grams for titles"],
                          ["Dense", "multilingual-e5-small, e5-base, bge-m3 (fp16, 384 tokens, exact search on GPU)"], ["Hybrid", "reciprocal rank fusion of BM25 and bge-m3, equal weights"],
                          ["English", "direct cross-lingual search vs query translation (NLLB-200) + lexical / dense / hybrid"]], [2.2, 9.9], size=16, row_h=0.65)

# 9 main result
s = new_slide("Main result: meaning beats words", f"bge-m3 finds the answer in the top 10 for {f2(b_ru['success@10'])} (ru), {f2(b_kk['success@10'])} (kk), {f2(b_en['success@10'])} (en)",
              "Success at ten is the share of questions where a judged answer is among the first ten results. bge-m3 is far ahead of BM25 in both languages, and it handles English queries directly. Intervals are wide with 45 needs, but the paired tests on the next slide show which differences are real.")
s.shapes.add_picture(str(FIG / "fig_success10.png"), Inches(0.5), Inches(1.7), width=Inches(12.3))
bullets(s, 0.6, 5.6, 12.1, 1.4, [f"MRR@10: bge-m3 {f3(b_ru['mrr@10'])} vs BM25 {f3(bm_ru['mrr@10'])} (ru); {f3(b_kk['mrr@10'])} vs {f3(bm_kk['mrr@10'])} (kk); intervals do not overlap.",
                                  "The equal-weight hybrid is worse than bge-m3 alone: the weak BM25 pulls the ranking down."], size=15, gap=5)

# 10 significance
s = new_slide("Which differences are real", "Paired bootstrap over needs and an exact sign test (Success@10, 45 needs)",
              "bge-m3 is significantly better than BM25 in both languages and, in Kazakh, better than both e5 models. In Russian bge-m3 and e5-base are not distinguishable. The hybrid is significantly worse than bge-m3. The three English strategies cannot be separated.")
names = {"bge-m3": "bge-m3", "bm25": "BM25", "e5-base": "e5-base", "e5-small": "e5-small", "hybrid": "hybrid", "cross": "EN direct", "translated": "EN translated", "hybrid_translated": "EN hybrid+transl."}
rows = [["Lang", "A vs B", "Δ Success@10 [95% CI]", "only A / only B", "p"]]
for t in SIG["tests"]:
    if (t["lang"], t["a"], t["b"]) in (("ru", "bge-m3", "bm25"), ("kk", "bge-m3", "bm25"), ("ru", "bge-m3", "e5-base"), ("kk", "bge-m3", "e5-base"), ("ru", "bge-m3", "hybrid"), ("kk", "bge-m3", "hybrid"), ("en", "cross", "translated")):
        d = t["s10_diff"]
        rows.append([t["lang"], f"{names[t['a']]} vs {names[t['b']]}", f"{d[0]:+.2f} [{d[1]:+.2f}; {d[2]:+.2f}]", f"{t['a_only']} / {t['b_only']}", "<0.001" if t["sign_p"] < 0.001 else f"{t['sign_p']:.3f}"])
table(s, 0.6, 1.9, 12.1, rows, [1.1, 4.2, 3.6, 2.0, 1.2], size=15, row_h=0.55)

# 11 other findings
s = new_slide("What else we found", "Kazakh stemming, corpus scope and English queries",
              "For Russian, stemming is clearly better than word forms. For Kazakh a five-letter prefix is as good as our suffix stemmer, so the naive suffix stripping gave no gain. Searching all text instead of articles lowers every system but keeps the ranking. For English, bge-m3 needs no translation; for e5 translation helps.")
s.shapes.add_picture(str(FIG / "fig_scope.png"), Inches(0.5), Inches(1.7), width=Inches(5.9))
s.shapes.add_picture(str(FIG / "fig_english.png"), Inches(6.9), Inches(1.7), width=Inches(5.9))
bullets(s, 0.6, 5.0, 12.1, 2.0, ["Word processing|: Russian stemming 0.42 vs 0.24 for word forms; Kazakh: prefix of 5 letters is as good as our suffix stemmer.",
                                  "More text, lower quality|: BM25 on Russian 0.42 → 0.18 when all 1.7 M passages are searched.",
                                  "English|: bge-m3 searches ru/kk text with an English query at 0.69 without translation."], size=15, gap=6)

# 11b recall table
UNI = jload("unified_comparison.json")["rows"]
s = new_slide("BM25 vs TF-IDF vs embeddings: Recall@k and MRR", "135 article queries (45 needs x 3 languages) + 24 title queries = 159 queries, 53 needs per language",
              "This is the comparison the topic asks for. Every method runs on the same queries and judgments. Recall at k is the share of judged answers found in the top k. BM25 beats TF-IDF and the keyword baseline, dense models beat BM25, and bge-m3 is far ahead. Numbers for Russian and Kazakh are shown; English is only possible for dense and translation-based methods.")
pick = ["Keyword overlap (baseline), stemming", "TF-IDF, stemming", "BM25, stemming", "Dense e5-small", "Dense e5-base", "Dense bge-m3", "Hybrid BM25 + bge-m3 (RRF)"]
pick_kk = ["Keyword overlap (baseline), 5-letter prefix", "TF-IDF, 5-letter prefix", "BM25, 5-letter prefix"] + pick[3:]
for k, (lang, names_, x) in enumerate((("ru", pick, 0.3), ("kk", pick_kk, 6.8))):
    rows = [["Method", "R@5", "R@10", "R@50", "MRR"]]
    for nm in names_:
        r = next(q for q in UNI if q["lang"] == lang and q["method"] == nm)
        rows.append([nm.replace(", stemming", "").replace(", 5-letter prefix", "").replace("Keyword overlap (baseline)", "Keyword overlap").replace("Hybrid BM25 + bge-m3 (RRF)", "Hybrid"), f2(r["recall@5"]), f2(r["recall@10"]), f2(r["recall@50"]), f3(r["mrr@10"])])
    textbox(s, x, 1.65, 6.0, 0.4, {"ru": "Russian queries", "kk": "Kazakh queries"}[lang], size=16, bold=True, color=BLUE)
    table(s, x, 2.1, 6.0, rows, [2.4, 0.8, 0.9, 0.9, 1.0], size=13, row_h=0.5)

# 11c part corpus
PART = jload("part_corpus_eval.json")
s = new_slide("bge-m3 on a part of the corpus", f"All {PART['articles']:,} articles + 15% of the other passages = {PART['passages']:,} passages ({PART['share_of_index']:.0%} of the index)",
              "Embedding the whole 1.7 million passages would take about eight GPU hours, so we embedded all articles plus a fixed random fifteen percent of the other passages. BM25 and e5-small were evaluated on exactly the same subset. bge-m3 keeps almost all of its quality when regulations and decisions are added, and it still beats the others by a wide margin.")
rows = [["System", "ru S@10", "ru MRR", "kk S@10", "kk MRR", "en S@10", "en MRR"]]
for nm in ("BM25", "e5-small", "bge-m3", "hybrid BM25 + bge-m3"):
    r = PART["systems"][nm]
    rows.append([nm] + sum(([f2(r[l]["success@10"]), f3(r[l]["mrr@10"])] if l in r else ["—", "—"] for l in ("ru", "kk", "en")), []))
table(s, 0.6, 1.9, 12.1, rows, [3.6, 1.4, 1.4, 1.4, 1.4, 1.4, 1.4], size=15, row_h=0.6)
bullets(s, 0.6, 5.4, 12.1, 1.5, [f"On the article index alone bge-m3 scores {f2(b_ru['success@10'])} / {f2(b_kk['success@10'])} / {f2(b_en['success@10'])} (ru / kk / en): adding a third of the corpus costs little.",
                                  "The added passages are mostly unjudged, so any drop is partly an incomplete-judgment effect."], size=15, gap=6)

# 12 cost
s = new_slide("Cost of quality", "RTX 3050 Laptop 4 GB, 16 GB RAM, fp16, 384 tokens",
              "bge-m3 encodes 53 passages per second, so the article index takes about an hour and the whole corpus about eight hours. We chose it because it is far better on Kazakh while a query still takes tens of milliseconds.")
rows = [["Method", "Index build", "Index size", "ms / query", "Success@10 ru / kk"],
        ["BM25", "tens of seconds", f"{bm_ru['index_mb']} MB", f"{bm_ru['ms_per_query']:.0f}", f"{f2(bm_ru['success@10'])} / {f2(bm_kk['success@10'])}"]]
for model, name, mins, dim in (("multilingual-e5-small", "e5-small", "8.9 min", 384), ("multilingual-e5-base", "e5-base", "27.0 min", 768), ("bge-m3", "bge-m3", "62.3 min", 1024)):
    r, k = g(DENSE, model=model, lang="ru", system="dense"), g(DENSE, model=model, lang="kk", system="dense")
    rows.append([name, mins, f"{319377 * dim * 2 // 1_000_000} MB", f"{r['ms_per_query']:.0f}", f"{f2(r['success@10'])} / {f2(k['success@10'])}"])
table(s, 0.6, 1.9, 12.1, rows, [2.4, 2.6, 2.4, 2.1, 2.6], size=16, row_h=0.62)
MEM = jload("memory_benchmark.json")
bullets(s, 0.6, 5.2, 12.1, 1.9, ["Encoding speed|: e5-small 377, e5-base 161, bge-m3 53 passages/s; part-corpus run took 69 min.",
                                  f"Loading the 952 MB CSV|: {MEM['loading'][0]['peak_mb']} MB peak with default types, {MEM['loading'][2]['peak_mb']} MB chunked; frame {MEM['loading'][0]['frame_mb']} → {MEM['loading'][4]['frame_mb']} MB with categories; Parquet {MEM['files']['parquet_mb']} MB.",
                                  f"Application|: {MEM['application']['after_load']['rss_mb']} MB RAM after start, {MEM['application']['after_20_searches']['gpu_allocated_mb']} MB GPU memory.",
                                  "Not run|: bge-m3 over all 1.7 M passages (about 8 GPU hours)."], size=15, gap=5)

# 13 ranking
s = new_slide("What improves ranking", "Variants fixed in advance on the same 45 needs",
              "We tested ideas fixed in advance, so we do not tune on a small set. Query instructions hurt bge-m3. The default status filters of the application, which hide old editions and bills, give by far the biggest gain. A small legal-force prior helps further but the test set is mostly codes, so it is off by default. The cross-encoder re-ranker costs six hundred milliseconds and adds nothing on top of the filters.")
s.shapes.add_picture(str(FIG / "fig_ranking.png"), Inches(0.5), Inches(1.6), width=Inches(8.0))
bullets(s, 8.7, 1.8, 4.3, 5.0, [f"Filters|: ru MRR@10 {f3(rv[('ru', 'base')]['mrr@10'])} → {f3(rv[('ru', 'filters')]['mrr@10'])}.", "Instructions|: hurt bge-m3.", "Legal-force prior|: helps, but test set is 78% codes → off by default.",
                                f"Re-ranker|: +{RANK['latency']['rr_title']['rerank_ms_per_query']} ms, no gain on top of filters."], size=15, gap=10)

# 14 robustness
s = new_slide("Robustness and honesty", "Typos, Latin letters, off-topic questions",
              "We perturbed the same 45 needs automatically. Typos and missing punctuation cost little. Russian typed in Latin letters fails until the engine also tries a back-transliteration. A similarity threshold flags off-topic questions; it separates them perfectly on our lists, but it was set on the same questions, so we call it unconfirmed.")
s.shapes.add_picture(str(FIG / "fig_robustness.png"), Inches(0.5), Inches(1.6), width=Inches(8.3))
sg = ROB["signal"]
bullets(s, 9.0, 1.8, 4.0, 5.0, [f"Latin Russian|: {f2(RB[('plain', 'ru', 'translit')]['s10'])} → {f2(RB[('fixed', 'ru', 'translit')]['s10'])} with back-transliteration.", f"No-answer warning|: AUC {sg['ru']['auc_top1']:.2f}; 20 off-topic + 6 borderline questions per language all flagged.",
                                "Caveat|: ~5% of real questions are flagged by construction; threshold unconfirmed."], size=15, gap=10)

# 15 application
s = new_slide("The application", "Standard-library web server + one page; engine in Python",
              "The user types a question in any language; the page detects the language, and the automatic mode decides between act search and article search. Exact article numbers are looked up directly. Cards show amendment history, highlighted deadlines and amounts, and links to the official site. The interface text is currently Russian.")
s.shapes.add_picture(str(OLD / "app_ru_search.jpg"), Inches(0.5), Inches(1.6), width=Inches(7.2))
bullets(s, 7.9, 1.7, 5.1, 5.2, ["Modes|: automatic, articles, act by title, compare acts, compare methods.", "Lookup|: “статья 188 УК” → the article itself.", "Layers|: filters, amendment history, deadlines and amounts, МРП → tenge, comparison of acts.",
                                "Warnings|: no reliable article; questions about evading the law.", "Languages|: queries and results in kk / ru / en; interface localisation into 3 languages is planned (screenshot: earlier build, Russian text)."], size=14, gap=7)

# 16 cited answer
sa = ANS["summary"]
s = new_slide("Optional answer from a local language model", f"{ANS['model']} (no API key needed); every sentence is checked",
              "The model answers only from the top four articles with numbered citations. A sentence is kept only if its citation exists, its numbers occur in the cited excerpt and its meaning is close to a sentence of that excerpt. In a manual read of forty-two kept sentences five were not supported, mostly in English and Kazakh. So the answer is shown as a draft with the closest article sentence next to it.")
rows = [["", "ru", "kk", "en"], ["Questions answered (of 45)"] + [str(sa[l]["answered"]) for l in ("ru", "kk", "en")], ["Gold article among the 4 excerpts"] + [str(sa[l]["gold_in_excerpts"]) for l in ("ru", "kk", "en")],
        ["Sentences without citation"] + [str(sa[l]["no_citation"]) for l in ("ru", "kk", "en")],
        ["Manual read: unsupported / read"] + [f"{sum(x['label'] == 'unsupported' for x in AUD if x['lang'] == l)} / {sum(1 for x in AUD if x['lang'] == l)}" for l in ("ru", "kk", "en")]]
table(s, 0.6, 1.9, 7.4, rows, [3.8, 1.2, 1.2, 1.2], size=14, row_h=0.6)
bullets(s, 8.4, 1.9, 4.5, 4.8, ["Catches|: invented citations and numbers.", "Misses|: distortions inside one article (“double” vs “one and a half”).", "Backend|: pluggable; Anthropic API backend written, not yet run (no key)."], size=15, gap=10)

# 17 errors
s = new_slide("Where it fails", "bge-m3 misses the judged article for 9 of 45 Russian needs",
              "Four error types: near but not judged articles, which is often incomplete judgments; another edition or bill, mostly removed by the filters; general versus special regime such as annual leave, which the comparison view addresses; and similar norms of other laws.")
table(s, 0.6, 1.9, 12.1, [["Error type", "Example", "What helps"],
                          ["Near, not judged article", "Adoption: articles 93, 95, 96 on consent", "More judgments"],
                          ["Another edition or bill", "Smoking in the Administrative Code: an older edition", "Status filters"],
                          ["General vs special regime", "Leave: law-enforcement service (30 days) above the Labour Code (24)", "Compare-acts view"],
                          ["Similar norm of another law", "Personal bankruptcy returns organisation bankruptcy", "Re-ranking did not fix it"]], [3.2, 6.0, 2.9], size=14, row_h=0.8)

# 18 conclusions
s = new_slide("Conclusions and limitations", None,
              "Conclusions first: semantic multilingual retrieval is clearly better than word matching, filtering and corpus checks matter as much as the model, and the extra layers were each tested. Limitations are important for honesty: judgments are ours and unreviewed, the set is small, and some thresholds were read from the same questions.")
textbox(s, 0.6, 1.3, 6.0, 0.5, "Conclusions", size=22, bold=True, color=GREEN)
bullets(s, 0.6, 1.9, 6.0, 5.0, [f"Meaning beats words|: bge-m3 {f2(b_ru['success@10'])} / {f2(b_kk['success@10'])} vs BM25 {f2(bm_ru['success@10'])} / {f2(bm_kk['success@10'])}; significant.", f"English without translation|: {f2(b_en['success@10'])}.",
                                "Filters matter|: status filters nearly double MRR@10.", "Check the data|: a linker bug had removed the main codes.", "Not helpful|: re-ranker, instructions, larger encoders, equal-weight hybrid."], size=16, gap=9)
textbox(s, 6.9, 1.3, 6.0, 0.5, "Limitations", size=22, bold=True, color=ACCENT)
bullets(s, 6.9, 1.9, 6.0, 5.0, ["Judgments drafted with an AI assistant, annotated in the team; no lawyer review.", "45 needs per language: intervals ±0.1.", "Thresholds and router read from the same questions.",
                                "bge-m3 not run on all 1.7 M passages; texts as of 01.04.2024.", "Interface text is Russian (localisation planned); no citation graph."], size=16, gap=9)

# 19 team & next
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
textbox(s, 0.9, 0.9, 11.5, 0.9, "Team contributions and next steps", size=36, bold=True, color=RGBColor(255, 255, 255))
bullets(s, 0.9, 2.0, 11.5, 4.5, ["Alisher Shayakhmetov|: the “brain” of the project — retrieval methods and models, evaluation, ranking and answer logic.", "Arsen Zhambekov|: data collection.", "Yernar Sakenov|: web site design, evaluation of the data and annotation.",
                                 "Next|: independent review of the judgments and a held-out question set; bge-m3 over all passages; evaluation of the answer with a stronger model.",
                                 "Code|: github.com/Alishershayakhmetov/legal_search (MIT); all datasets, models and papers used are credited with links in CREDITS.md."], size=20, gap=16)
for p in s.shapes:
    if p.has_text_frame:
        for para in p.text_frame.paragraphs:
            for r in para.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
s.notes_slide.notes_text_frame.text = "Contributions as stated by the team."

prs.save(str(OUT))
print("saved", OUT, "| slides", len(prs.slides))
