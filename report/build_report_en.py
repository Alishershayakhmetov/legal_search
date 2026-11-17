"""English written report (Word) for the final project; metrics come from outputs/*.json, other numbers are measurements recorded in docs/."""
import glob
import json
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "report" / "figures_en"
OUT = ROOT / "report" / "Report_Kazakh_Legal_Search_Engine.docx"


def load(pattern):
    rows = []
    for p in sorted(glob.glob(str(ROOT / "outputs" / pattern))):
        rows += json.loads(Path(p).read_text(encoding="utf-8"))
    return rows


def jload(name):
    return json.loads((ROOT / "outputs" / name).read_text(encoding="utf-8"))


SPARSE = load("sparse_results_articles_rukk_wordp5stem_v1_c2.json")
SPARSE_ALL = load("sparse_results_all_*_v1_c2.json")
DENSE = load("dense_results_*_articles_v1_c2.json")
DENSE_ALL = load("dense_results_multilingual-e5-small_all_v1_c2.json")
TITLE = load("title_results.json")
PAIRED, SIG = jload("paired_analysis.json"), jload("significance.json")
RANK, ROB, ANS, AUD = jload("rank_experiments.json"), jload("robustness.json"), jload("answer_eval.json"), jload("answer_audit.json")["items"]
AMD, RGM, PAR = jload("amendments.json")["stats"], jload("regimes.json"), jload("parallel_corpus.json")
SWEEP, SWEEP_T = jload("encoder_sweep.json"), {(x["model"], x["lang"]): x for x in jload("encoder_sweep_tests.json")}
MODELS = {"multilingual-e5-small": "e5-small", "multilingual-e5-base": "e5-base", "bge-m3": "bge-m3"}


def g(rows, **kw):
    return next(r for r in rows if all(r.get(k) == v for k, v in kw.items()))


def f2(x):
    return f"{x:.2f}"


def f3(x):
    return f"{x:.3f}"


def pfmt(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


doc = Document()
for s in doc.sections:
    s.top_margin, s.bottom_margin, s.left_margin, s.right_margin = Cm(2), Cm(2), Cm(2.3), Cm(2)
st = doc.styles["Normal"]
st.font.name, st.font.size = "Times New Roman", Pt(11)
st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
st.paragraph_format.space_after, st.paragraph_format.line_spacing = Pt(5), 1.1
for name, size in (("Heading 1", 15), ("Heading 2", 12.5), ("Heading 3", 11.5)):
    h = doc.styles[name]
    h.font.name, h.font.size, h.font.bold = "Times New Roman", Pt(size), True
    h.font.color.rgb = RGBColor(0x1F, 0x2A, 0x44)
    h.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    h.paragraph_format.space_before = Pt(12 if name == "Heading 1" else 9)
    h.paragraph_format.keep_with_next = True
counter = {"t": 0, "f": 0}


def p(text, bold=False, italic=False, align=None, size=None):
    para = doc.add_paragraph()
    run = para.add_run(text)
    run.bold, run.italic = bold, italic
    if size:
        run.font.size = Pt(size)
    if align == "center":
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    elif align == "justify":
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    return para


def body(text):
    return p(text, align="justify")


def bullets(items):
    for it in items:
        para = doc.add_paragraph(style="List Bullet")
        para.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        para.add_run(it)


def shade(cell, color):
    pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), color)
    pr.append(shd)


def table(title, header, rows, widths=None, size=8.5, bold_rows=()):
    counter["t"] += 1
    cap = p(f"Table {counter['t']} — {title}", italic=True, size=9.5)
    cap.paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, h in enumerate(header):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size = True, Pt(size)
        shade(c, "DCE6F2")
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            r = cells[i].paragraphs[0].add_run(str(v))
            r.font.size, r.bold = Pt(size), ri in bold_rows
    if widths:
        t.autofit = False
        for i, w in enumerate(widths):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Cm(w)
    for ri, row in enumerate(t.rows):
        for c in row.cells:
            for para in c.paragraphs:
                para.paragraph_format.space_after, para.paragraph_format.line_spacing = Pt(1), 1.0
                if len(t.rows) <= 22 and ri < len(t.rows) - 1:
                    para.paragraph_format.keep_with_next = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def figure(path, title, width_cm=15.5):
    doc.add_picture(str(path), width=Cm(width_cm))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    counter["f"] += 1
    cap = p(f"Figure {counter['f']} — {title}", italic=True, size=9.5, align="center")
    cap.paragraph_format.space_after = Pt(8)


def page_number(section):
    para = section.footer.paragraphs[0]
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = para.add_run()
    for tag, text in (("begin", None), (None, "PAGE"), ("end", None)):
        if tag:
            el = OxmlElement("w:fldChar")
            el.set(qn("w:fldCharType"), tag)
        else:
            el = OxmlElement("w:instrText")
            el.set(qn("xml:space"), "preserve")
            el.text = text
        run._r.append(el)


# ------------------------------------------------------------------ title page
for _ in range(4):
    doc.add_paragraph()
p("FINAL PROJECT", bold=True, align="center", size=14)
p("Programming for Data Analysis and Database — Applied Artificial Intelligence (MSc)", align="center", size=12)
doc.add_paragraph()
p("Topic 16 — Kazakh Legal Search Engine", bold=True, align="center", size=20)
p("Multilingual retrieval of articles of Kazakhstani legislation", bold=True, align="center", size=15)
p("queries in Kazakh, Russian and English; BM25 vs TF-IDF vs embeddings; Recall@k and MRR", align="center", size=11, italic=True)
for _ in range(4):
    doc.add_paragraph()
p("Team: Alisher Shayakhmetov, Arsen Zhambekov, Yernar Sakenov (as registered for topic 16)", align="center")
p("Group: AAI-2604", align="center")
p("Instructor: [name to be filled in]", align="center")
p("Code repository: [GitHub link to be filled in once the repository is published]", align="center")
doc.add_paragraph()
p("Astana, November 2026", align="center")
doc.add_page_break()
page_number(doc.sections[0])

b3, b3k, b3e = (g(DENSE, model="bge-m3", lang=l, system=s) for l, s in (("ru", "dense"), ("kk", "dense"), ("en", "dense_cross")))
bm_ru, bm_kk = g(SPARSE, lang="ru", analyzer="stem", scheme="bm25"), g(SPARSE, lang="kk", analyzer="p5", scheme="bm25")
rv = {(r["lang"], r["variant"]): r for r in RANK["summary"]}
S_ANS = ANS["summary"]

doc.add_heading("Abstract", level=1)
body("We built a search engine that takes an everyday question in Kazakh, Russian or English and returns the articles of Kazakhstani laws that answer it. "
     "The metadata of 223,245 legal acts (KazakhLawCorpus) were linked to the full texts of about 204,000 files of current legislation (Mendeley dataset "
     "“Textual Foundations of Justice”), the texts were cut into 3.12 million passages, and the metadata were loaded into a normalised SQLite database "
     "(13 tables, 13 SQL queries). We compared keyword overlap, TF-IDF, BM25 with three word-processing variants, dense retrieval with three multilingual embedding "
     "models (e5-small, e5-base, bge-m3) and their hybrids on a test set of 53 information needs (159 queries in three languages, 376 judged articles). "
     f"The best method is bge-m3: the right article is among the top ten results for {f2(b3['success@10'])} of Russian, {f2(b3k['success@10'])} of Kazakh and "
     f"{f2(b3e['success@10'])} of English queries (BM25: {f2(bm_ru['success@10'])} and {f2(bm_kk['success@10'])}; BM25 cannot serve English). "
     f"With the status filters of the web application, Success@10 rises to {f2(rv[('ru', 'filters')]['success@10'])} / {f2(rv[('kk', 'filters')]['success@10'])} / "
     f"{f2(rv[('en', 'filters')]['success@10'])}. On top of retrieval the system offers an article lookup by number, amendment history, an act-comparison view, "
     "a no-reliable-answer warning, robustness to typos and transliteration, and an optional answer written by a local language model with every sentence checked against the cited article. "
     "The results are provisional: the judgments were prepared by the project author with an AI assistant and have not been reviewed independently, and the test set is small.")

# ------------------------------------------------------------------ 1
doc.add_heading("1. Introduction and objectives", level=1)
body("Topic 16 asks for a search engine over Kazakhstani legal acts that retrieves relevant acts for a Kazakh query and compares BM25, TF-IDF and embeddings by Recall@k and MRR on at least 50 annotated queries. "
     "The source dataset contains metadata only (titles, kinds, bodies, dates), so a title-based engine finds an act by name but cannot answer a question such as "
     "“my employer has not paid my salary for two months, what can I do?”. We therefore extended the topic in three directions:")
bullets(["three query languages (Kazakh, Russian, English) although the corpus has no English text, which shapes the choice of methods;",
         "retrieval of articles, not only acts: the metadata are linked to full texts from a second source;",
         "an honest evaluation on judged everyday questions, with confidence intervals and significance tests, and an explicit account of what the judgments cannot show."])
body("The practical difficulties are the gap between everyday and legal vocabulary, the agglutinative morphology of Kazakh (one concept appears in dozens of word forms), many near-identical texts "
     "(bills, compilations and editions of one act), and truncated, ambiguous act titles in the sources. Appendix A maps every requirement of the course to the place where it is met.")

# ------------------------------------------------------------------ 2 DATA
doc.add_heading("2. Data", level=1)
doc.add_heading("2.1 Sources", level=2)
table("Data sources", ["Source", "Content", "Size", "Licence", "Role"], [
    ["KazakhLawCorpus (Hugging Face) [1]", "Act metadata: Kazakh/Russian titles, kind, body, dates, status, adilet link", "223,245 acts, 952 MB CSV", "Apache 2.0 (as recorded at download)", "Backbone: one record per act"],
    ["Textual Foundations of Justice (Mendeley Data) [2]", "Full texts of current acts as of 01.04.2024, .txt", "102,596 Russian (3.71 GB) and 101,304 Kazakh (3.41 GB) files", "CC BY 4.0", "Texts for article search"],
    ["adilet.zan.kz [3]", "Official database; pages are built with JavaScript, API disallowed in robots.txt", "—", "—", "Link-out only; nothing was scraped"],
], widths=[3.4, 4.8, 3.4, 2.2, 2.8])
body("The Mendeley archives were checked against their published SHA-256 sums. The files law_history.csv and law_references.csv promised in the KazakhLawCorpus description are not in the repository (HTTP 404), so a citation graph could not be built. "
     "The topic list suggests the “-clean” variant of the dataset; we used the metadata of the main repository and rely on our own audit below (Section 2.2). Mass downloading from adilet.zan.kz was not attempted.")
doc.add_heading("2.2 Loading, memory and metadata audit", level=2)
body("The 952 MB CSV is read in chunks of 100,000 rows; 22 of the 49 columns are kept and the result is stored as Parquet with zstd compression: 30 MB (31 times smaller), five seconds for the whole load. "
     "Memory use before and after dtype optimisation was not measured separately; the saving comes from the columnar format and categorical types. The audit of the metadata found:")
table("Metadata audit", ["Check", "Finding", "Action"], [
    ["Duplicate law_id", "0", "—"],
    ["Empty Kazakh title", "3.3% of acts; 57 titles are the text of a CAPTCHA (“Робот емес екеніңізді растаңыз”)", "Empty ones not loaded; CAPTCHA flagged is_placeholder"],
    ["Adoption date", "6 acts without a date; range 1947–2026; 383 acts before 1991", "Column allows NULL"],
    ["Publication date", "missing for 198,124 acts (89%)", "Not used"],
    ["is_archive", "constant 'f'", "Not used"],
    ["is_repealed", "34.5% of acts repealed (76,915)", "“In force only” filter in search"],
    ["Reference fields", "legal_force and database_section mix Kazakh and Russian text", "Stored as is"],
    ["Multi-valued fields", "act form: 43% of rows have several values; area of regulation: 76%; bodies with bracketed notes", "Many-to-many tables; split at a comma before a capital letter"],
    ["Look-alike letters", "Latin letters inside Cyrillic words (“отpасли”)", "Normalised in the tokenizer"],
], widths=[3.2, 7.4, 6.0])
doc.add_heading("2.3 Relational schema and SQL", level=2)
body("The data are loaded into SQLite (1.0 GB) in third normal form: the act table, titles in two languages (act_title), six look-up tables (form, area, body, region, legal force, database section), "
     "three many-to-many tables (act_form, act_area, act_body), the text_file table and passage metadata. The passage table has no law_id or lang column because both follow from file_id. The foreign-key check found no violations.")
figure(ROOT / "docs" / "er_diagram.png", "ER diagram of the database", 15)
body("Thirteen queries (sql/queries.sql) use CTEs, joins through the link tables, GROUP BY with HAVING, subqueries and the window functions LAG, RANK, ROW_NUMBER, SUM OVER and AVG OVER; the results are loaded into pandas and saved as CSV.")
table("SQL queries", ["#", "Question", "Techniques", "Finding"], [
    ["1", "Acts per year", "CTE, LAG", "Growth from 380 acts in 1991 to thousands a year"],
    ["2", "Share of repealed acts by body (≥500 acts)", "JOIN, HAVING, RANK", "Highest: the financial-market regulator (87.4%)"],
    ["3", "Top three areas of each decade", "two CTEs, ROW_NUMBER", "“Normative legal acts” leads"],
    ["4", "Text coverage of current vs repealed acts", "LEFT JOIN, conditional aggregation", "59.9% vs 4.5%"],
    ["5", "Link quality by match type", "GROUP BY, SUM OVER", "Mostly unambiguous title matches"],
    ["6", "Missing Kazakh titles by decade", "LEFT JOIN with subquery", "60–85% missing in 1950–1980s, 3% later"],
    ["7", "How many acts share a title", "nested aggregation, CASE", "40% of acts have a non-unique title"],
    ["8", "Most repeated titles", "JOIN, HAVING", "“On establishing a public easement”: 876 acts"],
    ["9", "Cumulative acts in the five largest regions", "IN subquery, SUM OVER", "—"],
    ["10", "Areas per act by kind", "correlated subquery", "Highest for amendment acts"],
    ["11", "Largest texts relative to the kind average", "JOIN, AVG OVER", "Curricula and standards stand out"],
    ["12", "Acts with most articles", "three JOINs, COUNT DISTINCT", "Codes; also draft codes"],
    ["13", "Share of articles, other text and tables", "CASE, SUM OVER", "8% / 52% / 40% (before the chunker fix)"],
], widths=[0.8, 5.4, 4.4, 6.0])
doc.add_heading("2.4 Linking texts to acts", level=2)
body("The Mendeley files are named by act title, status label (“Новый”, “Обновленный”), kind, body and date with number, truncated to 200 characters; there is no act identifier. "
     "Linking uses the normalised beginning of the file name against the title, then the date in the tail of the name and the act registry number, then body and region. "
     "When several acts share a title (for example budgets of different districts) and the date is cut off, the act is left undetermined and the file stays searchable without a link to an act.")
table("Result of linking files to acts", ["", "Russian", "Kazakh"], [
    ["Files", "102,596", "101,304"], ["Linked to one act", "79.8%", "81.1%"], ["Distinct acts with text", "80,916", "78,250"],
    ["Acts with text in both languages", "68,111", "—"], ["Check: date in file name = adoption date (unambiguous matches)", "96.8%", "98.7%"],
    ["Undetermined (ambiguous, truncated, no match)", "17,214 + 3,390 + 120", "11,192 + 5,920 + 2,049"],
], widths=[8.5, 4, 4])
body("The first version of the linker had a bug: titles shorter than five words (“Трудовой кодекс Республики Казахстан”, the Administrative Offences, Criminal and Land Codes) were not matched, so the most important acts had no text "
     "(2,392 Russian files without a match). We found it while preparing the test set and fixed it with the rule “a short title is accepted only if a status label follows it”; 120 files remained unmatched and the date check returned to 96.8%. "
     "Coverage is uneven: 59.9% of current acts have text but only 4.5% of repealed ones, because the Mendeley set contains current legislation.")
doc.add_heading("2.5 Chunking", level=2)
body("Acts with article headings (“Статья N.”, “N-бап.”, also without the full stop) are cut into articles; a long article is split at sentence boundaries into passages of up to 1,500 characters with 200 characters of overlap. "
     "Other acts are cut by paragraph. Passages with almost no letters (tables of digits) are dropped; tables with enough letters are kept with an is_table flag. "
     "The first run missed headings without a full stop (the Constitution and about 2,700 files per language, mostly treaties); after the fix the whole pipeline was re-run: 319,377 article passages instead of 230,545, and all metrics were recomputed.")
table("Result of chunking", ["Measure", "Russian", "Kazakh"], [
    ["Passages", "1,628,856", "1,495,552"], ["Median length, characters", "1,415", "1,418"],
    ["Article / other text / table passages", "10.9% / 49.5% / 39.6%", "11.1% / 49.7% / 39.1%"], ["Exact duplicate texts", "9.0%", "7.0%"],
    ["Passages in search indexes (no tables, no duplicates)", "888,356", "840,322"], ["of which article passages", "319,377 (both languages)", ""],
], widths=[8.5, 4, 4])
body("When duplicates are removed the copy that belongs to a real act is kept, not the one from a bill or compilation, otherwise judged articles would be replaced by bill text. Chunking the whole 7.1 GB takes about two minutes per language on 15 processes.")
doc.add_heading("2.6 Test set, judgments and leakage control", level=2)
body("The test set has 53 information needs: 30 everyday situations (“My employer says my position is being eliminated. What payments and protections am I entitled to?”), 15 concept questions and 8 act-title lookups, "
     "covering labour, civil, family, tax, administrative, criminal, procedural, land and housing law, business, social benefits and personal data. Each need is written in three languages (159 queries). "
     "Judgments are given for an (act, article) pair; versions of one act are merged by comparing the hash of the text, so a retrieved passage counts as a hit if its text equals the judged article. "
     "Results are collapsed to distinct findings, as the web interface groups passages by article.")
table("Judgments", ["Version", "How obtained", "Judged", "Answers (2)", "Related (1)", "Rejected (0)"], [
    ["v0", "Articles chosen by hand from legal knowledge and heading search; text read for 54 of 102", "102", "58", "44", "—"],
    ["v1", "Added the top results of eight system runs (pooling [12]): 270 candidates", "376", "67", "100", "209"],
], widths=[1.3, 8.0, 1.8, 1.9, 1.9, 1.9])
body("All judgments were prepared by the author with an AI assistant; they were not reviewed by a lawyer or a second annotator, and the Kazakh queries were not checked by a native speaker. The pool comes from the systems that are compared, which slightly favours them, "
     "and 52 of the 67 grade-2 judgments are articles of codes. No model is trained or tuned on the questions (all models are used as published), so there is no train/test leakage in the model comparison; "
     "the few thresholds chosen later (Sections 4.7–4.9) were read from the same questions and are flagged as unconfirmed.")

# ------------------------------------------------------------------ 3 METHODS
doc.add_heading("3. Methods", level=1)
figure(FIG / "fig_pipeline.png", "Data and search pipeline", 16)
doc.add_heading("3.1 Search layers and text processing", level=2)
body("Search runs over two layers: act titles (439,124 Russian and Kazakh titles) and article passages (319,377 passages for questions; an index over all text with 1,728,678 passages is used to test the effect of noise). "
     "Three word-processing variants were compared: word forms; the first five letters of a word (a simple device for agglutinative languages); and stemming — Snowball for Russian [10] and our own iterative suffix stripping for Kazakh "
     "(plural, possessive and case endings, minimum stem three letters). For titles, character n-grams of length 3–5 were also tested. Stop words are removed, ё becomes е, Latin look-alike letters in Cyrillic words are replaced by Cyrillic ones.")
doc.add_heading("3.2 Retrieval methods", level=2)
bullets(["Baseline: number of matched query words (keyword overlap), ties broken by the shorter passage.",
         "TF-IDF with cosine similarity and BM25 [4] (k1 = 1.2, b = 0.75, not tuned). The index is a sparse matrix over hashed words (2^23 features); a query touches only the posting lists of its words.",
         "Dense retrieval: multilingual-e5-small and e5-base [5] (with “query:”/“passage:” prefixes) and bge-m3 [6]; fp16, up to 384 tokens, exact dot product on the GPU, no approximate index.",
         "Hybrid: reciprocal rank fusion (RRF) [8] of BM25 and dense results with equal weights."])
doc.add_heading("3.3 English queries", level=2)
body("The corpus has no English text. Two strategies were tested: direct cross-lingual search (the English query against Russian and Kazakh passages with a multilingual model) and translation of the query with NLLB-200 (600M parameters) [7] into Russian and Kazakh followed by lexical, dense or hybrid search.")
doc.add_heading("3.4 Evaluation protocol", level=2)
body("Metrics are Success@k (at least one relevant article in the top k), Recall@50, MRR@10 and nDCG@10 [9]; 95% confidence intervals come from a bootstrap over needs [11]. "
     "Methods are compared on the same needs with a paired bootstrap of the difference and an exact sign test on the discordant needs. Figures are for the 45 situation and concept needs per language (title lookups are evaluated separately); "
     "unless stated otherwise the index covers articles only.")
doc.add_heading("3.5 Layers added after retrieval", level=2)
bullets(["Status filters (default): hide repealed acts, bills/compilations and amending acts. Optional prior: a small bonus by legal force of the act kind (Constitution > constitutional law > code > law > decree), off by default.",
         "Exact article lookup: a query such as “статья 188 УК” or “ст. 52 ТК РК” finds the act by title and the article by number; abbreviations (ТК, ГК, УК, ОСМС, МРП …) are spelled out before encoding.",
         "Automatic mode: a short query whose best act title is closer than its best article is routed to act search; everything else goes to article search.",
         "Robustness and honesty: a query typed in Latin letters is also read as transliterated Russian; a warning is shown when the best similarity is below a per-language threshold; questions about evading the law get a notice (docs/policy.md).",
         "Reading aids: amendment history and pending-change warnings parsed from the footnotes of the texts, deadlines and amounts highlighted, monthly calculation indices converted to tenge, an act-comparison view, key sentences, optional machine translation of a snippet.",
         "Cited answer: a local language model (Ollama, gemma3:4b) answers from the top four articles; each sentence is checked (existing citation, numbers present in the cited excerpt, bge-m3 similarity ≥ 0.65 to a sentence of the cited excerpt) and failing sentences are dropped."])
doc.add_heading("3.6 Software architecture", level=2)
body("Python 3 only. src/ holds the numbered pipeline scripts (download, Parquet conversion, linking, SQLite, chunking, indexing, embedding, evaluation); src/search_lib.py, chunking.py, textproc.py and evaluate.py are the libraries. "
     "app/ contains the engine (engine.py), a standard-library HTTP server (server.py) with one HTML page, and the modules amendments.py, answer.py and llm.py. 43 unit tests and 28 behaviour tests on the real index run with pytest; a GitHub Actions workflow runs the unit tests.")

# ------------------------------------------------------------------ 4 RESULTS
doc.add_heading("4. Results", level=1)
body("95% confidence intervals for MRR@10 are about ±0.1 with 45 needs per language, so differences of a few points are not evidence.")
doc.add_heading("4.1 Word processing and weighting schemes", level=2)
rows = []
for lang in ("ru", "kk"):
    for mode in ("word", "p5", "stem"):
        ov, tf, bm = (g(SPARSE, lang=lang, analyzer=mode, scheme=s) for s in ("overlap", "tfidf", "bm25"))
        rows.append([lang, {"word": "word forms", "p5": "5 letters", "stem": "stemming"}[mode], f2(ov["success@10"]), f2(tf["success@10"]), f2(bm["success@10"]), f3(bm["mrr@10"])])
table("Success@10 of keyword overlap, TF-IDF and BM25 with three word-processing variants (article index)", ["Language", "Processing", "Keywords", "TF-IDF", "BM25", "MRR@10 (BM25)"], rows, widths=[2, 3.2, 3, 2.6, 2.6, 3])
body("BM25 beats TF-IDF and the baseline under every processing variant. For Russian, stemming clearly helps (Success@10 0.42 vs 0.31 for five letters and 0.24 for word forms). "
     "For Kazakh the three variants tie on Success@10 (0.31) and the simple five-letter prefix is best on MRR@10 (0.166 vs 0.132 for word forms and 0.118 for our suffix stemmer): naive suffix stripping gave no gain, so the application uses the five-letter prefix for Kazakh.")
doc.add_heading("4.2 System comparison", level=2)
rows = []
for lang, mode in (("ru", "stem"), ("kk", "p5")):
    bm = g(SPARSE, lang=lang, analyzer=mode, scheme="bm25")
    rows.append([lang, f"BM25 ({'stemming' if lang == 'ru' else '5 letters'})", f2(bm["success@5"]), f2(bm["success@10"]), f2(bm["recall@50"]), f3(bm["mrr@10"]), f3(bm["ndcg@10"]), f"{bm['ms_per_query']:.0f}"])
    for model, label in MODELS.items():
        d = g(DENSE, model=model, lang=lang, system="dense")
        rows.append([lang, label, f2(d["success@5"]), f2(d["success@10"]), f2(d["recall@50"]), f3(d["mrr@10"]), f3(d["ndcg@10"]), f"{d['ms_per_query']:.0f}"])
    h = g(DENSE, model="bge-m3", lang=lang, system="hybrid")
    rows.append([lang, "hybrid BM25 + bge-m3", f2(h["success@5"]), f2(h["success@10"]), f2(h["recall@50"]), f3(h["mrr@10"]), f3(h["ndcg@10"]), f"{h['ms_per_query']:.0f}"])
table("System comparison on articles (judgments v1, no status filters)", ["Lang", "System", "S@5", "S@10", "R@50", "MRR@10", "nDCG@10", "ms/query"], rows, widths=[1.3, 5, 1.6, 1.6, 1.6, 2, 2, 1.8], bold_rows=(3, 8))
figure(FIG / "fig_success10.png", "Success@10 by system and query language (article index)", 15.5)
body(f"Dense retrieval beats BM25 in both languages and bge-m3 beats every other system; MRR@10 intervals of bge-m3 and BM25 do not overlap (Russian {f3(b3['mrr@10'])} vs {f3(bm_ru['mrr@10'])}, Kazakh {f3(b3k['mrr@10'])} vs {f3(bm_kk['mrr@10'])}). "
     "e5-base is worse than e5-small on Kazakh (0.36 vs 0.49), with overlapping intervals and no explanation in the data. The equal-weight hybrid is worse than bge-m3 alone because the weaker BM25 pulls the ranking down; weights were not tuned, to avoid fitting 45 questions.")
pr, pk = PAIRED["paired_success_at_10"]["ru"], PAIRED["paired_success_at_10"]["kk"]
table("Paired view of BM25 and bge-m3 by need (Success@10, 45 needs)", ["Language", "Both find", "Only bge-m3", "Only BM25", "Neither"],
      [["Russian", pr["both"], pr["only_bge_m3"], pr["only_bm25"], pr["neither"]], ["Kazakh", pk["both"], pk["only_bge_m3"], pk["only_bm25"], pk["neither"]]], widths=[3, 3, 3.2, 3.2, 3])
NAMES = {"bge-m3": "bge-m3", "bm25": "BM25", "e5-base": "e5-base", "e5-small": "e5-small", "hybrid": "hybrid", "cross": "English direct", "translated": "translated query", "hybrid_translated": "hybrid + translation"}
sig_rows = []
for tt in SIG["tests"]:
    d = tt["s10_diff"]
    sig_rows.append([tt["lang"], f"{NAMES[tt['a']]} / {NAMES[tt['b']]}", f"{tt['s10_a']:.2f} / {tt['s10_b']:.2f}", f"{d[0]:+.2f} [{d[1]:+.2f}; {d[2]:+.2f}]", f"{tt['a_only']} / {tt['b_only']}", pfmt(tt["sign_p"])])
table("Paired comparisons (Success@10, 45 needs; difference A − B with a 95% bootstrap interval over needs)", ["Lang", "A / B", "Success@10", "Difference", "Only A / only B", "Sign test p"], sig_rows, widths=[1.2, 5, 2.3, 3.6, 2.5, 2.0], size=8)
body("bge-m3 is significantly better than BM25 in both languages and, on Kazakh, better than both e5 models. On Russian the difference between bge-m3 and e5-base is not established (the interval includes zero). The equal-weight hybrid is significantly worse than bge-m3 alone. "
     "The three ways of searching with English queries cannot be told apart statistically with 45 needs.")
tp = SIG["breakdown"]
body(f"By need type bge-m3 does better on concept questions than on everyday situations (Success@10 {tp['ru']['type']['concept']['s10']:.2f} vs {tp['ru']['type']['situation']['s10']:.2f} in Russian, {tp['kk']['type']['concept']['s10']:.2f} vs {tp['kk']['type']['situation']['s10']:.2f} in Kazakh). "
     f"The weakest topics are procedure ({tp['ru']['topic']['procedure']['s10']:.2f} in Russian, 3 needs) and civil law in Kazakh ({tp['kk']['topic']['civil']['s10']:.2f}, 4 needs); groups of 1–7 needs are too small for conclusions.")
doc.add_heading("4.3 Effect of corpus size and composition", level=2)
figure(FIG / "fig_scope.png", "Success@10 on an index of articles only and on all text", 11.5)
rows = []
for lang, mode in (("ru", "stem"), ("kk", "p5")):
    a, fl = g(SPARSE, lang=lang, analyzer=mode, scheme="bm25"), g(SPARSE_ALL, lang=lang, analyzer=mode, scheme="bm25")
    rows.append([lang, f"BM25 ({mode})", f"{a['n_docs']:,}", f2(a["success@10"]), f"{fl['n_docs']:,}", f2(fl["success@10"]), f"{fl['index_mb']} MB"])
    d1, d2 = g(DENSE, model="multilingual-e5-small", lang=lang, system="dense"), g(DENSE_ALL, lang=lang, system="dense")
    rows.append([lang, "e5-small", "—", f2(d1["success@10"]), "—", f2(d2["success@10"]), ""])
table("Effect of corpus composition", ["Lang", "System", "Articles: passages", "S@10", "All text: passages", "S@10", "BM25 index"], rows, widths=[1.3, 3, 3.2, 1.6, 3.3, 1.6, 2.4])
body("Adding regulations, decisions and other text lowers every system (BM25 on Russian: 0.42 → 0.18) but the ranking of the systems is preserved. Part of the loss comes from incomplete judgments: added documents may be relevant but are not judged. "
     "bge-m3 over all passages was not run (about 8 GPU hours on this laptop), so the best model is verified only on the article index.")
doc.add_heading("4.4 English queries", level=2)
figure(FIG / "fig_english.png", "Success@10 for English queries: direct search vs query translation", 11.5)
rows = []
for model in MODELS:
    for system, label in (("dense_cross", "direct"), ("bm25_translated", "translate + BM25"), ("dense_translated", "translate + dense"), ("hybrid_translated", "translate + hybrid")):
        r = g(DENSE, model=model, lang="en", system=system)
        rows.append([MODELS[model], label, f2(r["success@5"]), f2(r["success@10"]), f2(r["recall@50"]), f3(r["mrr@10"])])
table("English queries", ["Model", "Strategy", "S@5", "S@10", "R@50", "MRR@10"], rows, widths=[3, 4.4, 2, 2, 2, 2.4])
body("bge-m3 searches Russian and Kazakh text with an English query almost as well as with a Russian one (0.69 vs 0.80) and needs no translation. For the e5 models direct cross-lingual search is weak (0.13–0.22) and query translation helps a lot; the best strategy for e5-small is translation with a hybrid.")
doc.add_heading("4.5 Finding an act by title", level=2)
rows = [[t["lang"], t["system"], f2(t["success@1"]), f2(t["success@5"]), f2(t["success@10"]), f3(t["mrr@10"])] for lang in ("ru", "kk", "en") for t in TITLE if t["lang"] == lang]
table("Title layer (8 queries per language, e5-small)", ["Lang", "System", "S@1", "S@5", "S@10", "MRR@10"], rows, widths=[1.6, 5, 2, 2, 2, 2.4], size=8)
body("Eight queries per language are too few for conclusions (one query changes a metric by 0.125). In the application the title layer uses bge-m3 over all 439,124 titles.")
doc.add_heading("4.6 Cost: time, memory and index size", level=2)
n_art = 319377
rows = [["BM25 (stemming)", "tens of seconds", f"{g(SPARSE, lang='ru', analyzer='stem', scheme='bm25')['index_mb']} MB", f"{g(SPARSE, lang='ru', analyzer='stem', scheme='bm25')['ms_per_query']:.0f}", "—"]]
for model, mins, dim, params in (("multilingual-e5-small", "8.9", 384, "118M"), ("multilingual-e5-base", "27.0", 768, "278M"), ("bge-m3", "62.3", 1024, "568M")):
    rows.append([MODELS[model], mins + " min", f"{n_art * dim * 2 // 1_000_000} MB", f"{g(DENSE, model=model, lang='ru', system='dense')['ms_per_query']:.0f}", params])
table("Cost of the approaches (RTX 3050 Laptop 4 GB, 16 GB RAM, fp16, 384 tokens)", ["Method", "Index build (230,545 articles, full run)", "Index size (319,377)", "ms per query (Russian)", "Parameters"], rows, widths=[3, 4.6, 3.2, 3.4, 2.4])
body("Encoding speed at 384 tokens is 377 (e5-small), 161 (e5-base) and 53 (bge-m3) passages per second. Embedding the 66,538 new articles after the chunker fix took about an hour because the vectors of unchanged texts were reused (checked: re-encoding 300 random texts gives cosine ≥ 0.9995 with the stored vectors). "
     "A complete application search takes about 0.2 s once the encoder is loaded; the first query after start-up takes longer.")
doc.add_heading("4.7 Ranking improvements (fixed in advance, no tuning)", level=2)
figure(FIG / "fig_ranking.png", "MRR@10 of ranking variants on top of bge-m3", 14)
rows = []
RT = {(r["lang"], r["variant"]): r for r in RANK["tests_vs_base"]}
for key, label in (("base", "plain bge-m3 (reference)"), ("instr_ru", "query instruction"), ("filters", "default status filters"), ("filters+force_0.02", "filters + legal-force prior"),
                   ("rr_title", "re-ranker bge-reranker-v2-m3 on top 30"), ("filters+rr_title", "filters + re-ranker")):
    row = [label]
    for lang in ("ru", "kk", "en"):
        r, tt = rv[(lang, key)], RT.get((lang, key))
        row += [f2(r["success@10"]), f3(r["mrr@10"]), "—" if tt is None else pfmt(tt["sign_p"])]
    row.append(str(RANK["latency"][key]["total_ms_per_query"]))
    rows.append(row)
table("Ranking variants (45 needs per language; p = sign test on Success@10 against the reference)", ["Variant", "ru S@10", "MRR", "p", "kk S@10", "MRR", "p", "en S@10", "MRR", "p", "ms/query"], rows,
      widths=[4.6, 1.3, 1.2, 1.1, 1.3, 1.2, 1.1, 1.3, 1.2, 1.1, 1.4], size=7.5)
bullets(["Query instructions hurt bge-m3 in all languages: the model was trained without them.",
         f"The default status filters give by far the biggest gain (Russian MRR@10 {f3(rv[('ru', 'base')]['mrr@10'])} → {f3(rv[('ru', 'filters')]['mrr@10'])}, Success@1 {f2(rv[('ru', 'base')]['success@1'])} → {f2(rv[('ru', 'filters')]['success@1'])}): without them old editions and bills with near-identical text crowd the top. The unfiltered figures of Section 4.2 therefore understate what a user of the application sees.",
         "A small legal-force prior on top of the filters raises Russian Success@1 to " + f2(rv[('ru', 'filters+force_0.02')]['success@1']) + " and helps in all three languages, but 52 of 67 judged answers are code articles, so the test set itself rewards the prior; it is off by default until an independent set confirms it.",
         f"The cross-encoder re-ranker costs about {RANK['latency']['rr_title']['rerank_ms_per_query']} ms per query, improves the order alone but adds nothing on top of the filters; it was not adopted."])
doc.add_heading("4.8 Robustness and the no-reliable-answer warning", level=2)
figure(FIG / "fig_robustness.png", "Success@10 of the application under perturbed queries", 14)
RB = {(r["mode"], r["lang"], r["variant"]): r for r in ROB["summary"]}
SG = ROB["signal"]
body(f"Perturbed versions of the same 45 needs were generated automatically (seed 7). Typos and missing punctuation cost little; four-keyword queries and Latin-letter queries hurt. "
     f"For Russian typed in Latin letters the engine also tries a back-transliteration and keeps the reading with higher confidence (Success@10 {f2(RB[('plain', 'ru', 'translit')]['s10'])} → {f2(RB[('fixed', 'ru', 'translit')]['s10'])}; English queries are unchanged). "
     f"Kazakh in Latin letters loses letters (ә, қ, ұ …) and recovers only to {f2(RB[('fixed', 'kk', 'translit')]['s10'])}. Russian and Kazakh joined in one query: {f2(RB[('plain', 'mix', 'mixed')]['s10'])}.")
body(f"The top-1 cosine similarity separates in-scope from off-topic questions (AUC {SG['ru']['auc_top1']:.2f} / {SG['kk']['auc_top1']:.2f} / {SG['en']['auc_top1']:.2f} for ru / kk / en; the margin to the 10th result is useless, AUC about 0.57). "
     f"Thresholds {SG['ru']['threshold_top1_keep95']:.2f} / {SG['kk']['threshold_top1_keep95']:.2f} / {SG['en']['threshold_top1_keep95']:.2f} (5th percentile of in-scope questions) flag all 20 clearly off-topic and 6 borderline questions per language; about 5% of in-scope questions are flagged by construction. "
     "The thresholds were read from the same questions, so the false-flag rate on new questions is unconfirmed. The page shows a warning but still shows the results.")
doc.add_heading("4.9 Abbreviations, query router, amendments, act comparison", level=2)
ab = jload("abbreviations.json")
w_top1, e_top1 = sum(r["found_top1"] for r in ab if r["mode"] == "without"), sum(r["found_top1"] for r in ab if r["mode"] == "with")
router = jload("router.json")["accuracy"]["all"]
body(f"Abbreviations: on 14 questions written with abbreviations, spelling them out before encoding moves the expected act to the first result in {e_top1} cases instead of {w_top1} (5 better, none worse; descriptive, own questions). "
     f"Router: on the 159 test queries (24 titles, 135 questions) the rule is wrong {router['n'] - router['correct']} times, but the class gap is thin and the threshold was read from the same queries. "
     f"Amendments: footnotes exist for {AMD['ru_with_footnote']:,} Russian and {AMD['kk_with_footnote']:,} Kazakh articles and {AMD['ru_footnote_parsed'] / AMD['ru_with_footnote']:.1%} / {AMD['kk_footnote_parsed'] / AMD['kk_with_footnote']:.1%} are parsed ({AMD['entries']:,} entries); "
     "34 random parses were read by hand and the errors found were fixed. "
     f"Act comparison: the right act is among the five acts shown for {RGM['ru']['regimes_act']} of {RGM['ru']['n']} Russian and {RGM['kk']['regimes_act']} of {RGM['kk']['n']} Kazakh needs, while the exact article among the best-per-act articles is found less often than in the plain top five ({RGM['ru']['regimes_article']} vs {RGM['ru']['plain5']} in Russian), so the view complements the list.")
doc.add_heading("4.10 Cited answer from a local language model", level=2)
rows = []
for lang, name in (("ru", "Russian"), ("kk", "Kazakh"), ("en", "English")):
    s, it = S_ANS[lang], [x for x in AUD if x["lang"] == lang]
    rows.append([name, f"{s['answered']} / {s['questions']}", f"{s['gold_in_excerpts']} / {s['questions']}", str(s["sentences"]), f"{s['no_citation']} / {s['missing_excerpt']} / {s['number_not_in_excerpt']}",
                 f"{sum(x['label'] == 'unsupported' for x in it)} of {len(it)}", f"{sum(x['off_topic'] for x in it)} of {len(it)}"])
table(f"Answers of {ANS['model']} on the test questions", ["Language", "Answered", "Gold article among 4 excerpts", "Sentences", "No citation / missing excerpt / number not in excerpt", "Manual read: unsupported", "Manual read: off-topic"], rows,
      widths=[2, 2, 3, 2, 3.8, 2.4, 2.2], size=8)
body("The checks catch invented citations and numbers; they cannot catch a distortion inside one article. In a manual read of 42 random sentences that passed the checks (by the project author’s assistant, not a lawyer) 5 were not supported by the article (0 of 14 Russian, 2 of 12 Kazakh, 3 of 16 English), "
     "for example “night work is paid at least double” where the text says “not lower than one and a half times”. About a fifth of the sentences are faithful but do not answer the question. The answer is therefore shown as a draft with a view of the closest article sentence for each answer sentence. "
     "The backend is pluggable (app/llm.py): an Anthropic API backend is written but has not been run because no key was available.")
doc.add_heading("4.11 Error analysis", level=2)
body("bge-m3 misses the judged article in the top ten for 9 of 45 Russian needs. Four error types recur: (1) near but not judged articles (adoption: articles 93, 95, 96 on consent instead of the judged one), often an incomplete-judgment effect; "
     "(2) another edition or a bill with near-identical text (smoking, dismissal, appeal) — mostly removed by the status filters; (3) general versus special regime (annual leave returns the law on law-enforcement service, 30 days, above the Labour Code, 24 days) — addressed by the act-comparison view; "
     "(4) similar norms of other laws (bankruptcy of a person returns norms on the bankruptcy of organisations; filing a debt claim returns the debtor’s petition).")
doc.add_heading("4.12 Additional artefacts and a model sweep", level=2)
sw_rows = []
for name, label in (("BAAI/bge-m3", "bge-m3 (reference)"), ("intfloat/multilingual-e5-large", "multilingual-e5-large"), ("Qwen/Qwen3-Embedding-0.6B", "Qwen3-Embedding-0.6B")):
    row = [label]
    for lang in ("ru", "kk", "en"):
        s, tt = SWEEP[name]["summary"][lang], SWEEP_T.get((name, lang))
        row += [f2(s["success@10"]), f3(s["mrr@10"]), "—" if tt is None else pfmt(tt["sign_p"])]
    sw_rows.append(row)
table("Re-ranking of a shared candidate pool (about 255 articles per question)", ["Model", "ru S@10", "MRR", "p", "kk S@10", "MRR", "p", "en S@10", "MRR", "p"], sw_rows, widths=[4.6, 1.5, 1.4, 1.2, 1.5, 1.4, 1.2, 1.5, 1.4, 1.2], size=8)
body("Re-embedding 319,000 articles per model takes 1–2 hours, so each model re-ranks the same candidate pool (top 150 of bge-m3, top 100 of e5-base and of BM25). This compares re-ranking quality, not retrieval, and the pool favours bge-m3 slightly. "
     "No model beats bge-m3 significantly: e5-large equals it on Russian (p = 1) and is worse on Kazakh (p = 0.012); Qwen3-Embedding-0.6B is worse on Kazakh (p < 0.001). "
     f"As by-products, prepared locally and not published, we built a parallel Russian–Kazakh corpus of {PAR['pairs']:,} article pairs from {PAR['acts']:,} acts with an alignment check (a manual read of 43 pairs: 10 of 10 correct at cosine ≥ 0.8, about 4 of 15 below 0.6), "
     "a glossary of 204 recurring headings and 1,174 word pairs (46 of 50 sampled word pairs correct), and a test-set release package with a datasheet. Licences and instructor approval are still to be settled.")

# ------------------------------------------------------------------ 5 CONCLUSIONS
doc.add_heading("5. Conclusions", level=1)
bullets([f"Semantic multilingual retrieval clearly beats lexical retrieval for everyday legal questions: bge-m3 reaches Success@10 {f2(b3['success@10'])} (Russian), {f2(b3k['success@10'])} (Kazakh) and {f2(b3e['success@10'])} (English, no translation) against BM25 {f2(bm_ru['success@10'])} and {f2(bm_kk['success@10'])}; the differences are statistically significant.",
         "What is indexed and filtered matters as much as the model: removing repealed acts, bills and amending acts almost doubles MRR@10, and the corpus must be checked (a linker bug had silently removed the main codes).",
         "For Kazakh a five-letter prefix is as good as, or better than, a hand-written suffix stemmer for BM25; for Russian stemming helps.",
         "A cross-encoder re-ranker, query instructions, larger encoders (e5-large, Qwen3-0.6B) and an equal-weight hybrid did not help once the better setup was in place.",
         "The application adds the layers a user needs (article lookup, amendment history, comparison of acts, warnings, robustness, optional checked answer), each with a test and a measurement or an explicit statement that it was not measured."])
doc.add_heading("Limitations", level=3)
bullets(["Judgments were prepared by the author with an AI assistant, are incomplete and unreviewed; the Kazakh queries were not checked by a native speaker; 52 of the 67 grade-2 judgments are code articles.",
         "Small test set (45 needs per language): intervals are wide; thresholds and rules added later were read from the same questions.",
         "Texts are a snapshot of 01.04.2024 covering mostly current legislation; the citation graph and the history of editions are not available.",
         "bge-m3 was not run on all 1.7 million passages; the LLM answer is checked only sentence by sentence and by a small manual read; the Anthropic backend has not been run.",
         "The web interface is in Russian; there is no console menu and Streamlit was removed in favour of a standard-library web page."])
doc.add_heading("Future work", level=3)
bullets(["Independent review of the judgments and a held-out set written by other people; then re-estimate every threshold and the legal-force prior on it.",
         "bge-m3 over all passages; citation graph if the missing files appear; edition history by date.",
         "Evaluation of the cited answer with a stronger model through the existing backend interface and a larger human audit."])

# ------------------------------------------------------------------ References
doc.add_heading("References", level=1)
refs = ["[1] KazakhLawCorpus, Hugging Face dataset, Arailym-tleubayeva/KazakhLawCorpus (metadata of Kazakhstani legal acts).",
        "[2] Textual Foundations of Justice: Kazakhstani laws and jurisprudence dataset, Mendeley Data, https://data.mendeley.com/datasets/jdpc5658nh (CC BY 4.0).",
        "[3] Information system “Adilet”, Ministry of Justice of the Republic of Kazakhstan, https://adilet.zan.kz.",
        "[4] S. Robertson, H. Zaragoza. The Probabilistic Relevance Framework: BM25 and Beyond. Foundations and Trends in Information Retrieval 3(4), 2009.",
        "[5] L. Wang et al. Text Embeddings by Weakly-Supervised Contrastive Pre-training (E5) and Multilingual E5 Text Embeddings: A Technical Report, arXiv:2212.03533, arXiv:2402.05672.",
        "[6] J. Chen et al. BGE M3-Embedding: Multi-Lingual, Multi-Functionality, Multi-Granularity Text Embeddings Through Self-Knowledge Distillation, arXiv:2402.03216, 2024.",
        "[7] NLLB Team. No Language Left Behind: Scaling Human-Centered Machine Translation, arXiv:2207.04672, 2022.",
        "[8] G. Cormack, C. Clarke, S. Büttcher. Reciprocal Rank Fusion outperforms Condorcet and individual rank learning methods. SIGIR 2009.",
        "[9] K. Järvelin, J. Kekäläinen. Cumulated gain-based evaluation of IR techniques. ACM TOIS 20(4), 2002.",
        "[10] M. Porter. Snowball: A language for stemming algorithms, 2001; NLTK implementation.",
        "[11] B. Efron, R. Tibshirani. An Introduction to the Bootstrap. Chapman & Hall, 1993.",
        "[12] K. Sparck Jones, C. J. van Rijsbergen. Report on the need for and provision of an “ideal” information retrieval test collection. British Library R&D Report 5266, 1975.",
        "[13] Gemma Team. Gemma 3 Technical Report, arXiv:2503.19786, 2025 (the local model used for answers)."]
for r in refs:
    para = p(r, size=10)
    para.paragraph_format.space_after = Pt(2)

# ------------------------------------------------------------------ Appendices
doc.add_heading("Appendix A. Requirement checklist", level=1)
table("Course requirements and where they are met", ["Requirement", "Where"], [
    ["1 ≥5 functions; 2 lists/dicts; 3 conditions; 4 loops", "Throughout src/ and app/ (e.g. chunking.py, search_lib.py, evaluate.py, engine.py)"],
    ["5 File reading and writing", "Parquet, CSV, JSON, SQLite files; feedback log; judgments in annotation/*.json"],
    ["6 try/except", "Download and extraction (00_download_data.py), feedback logging, server request handling, LLM backend errors"],
    ["7 User interface", "Web mini-dashboard with filters (app/server.py + app/static/index.html); there is no console menu"],
    ["8 Modularity", "src/ library modules, app/ package, about 50 numbered scripts, standard libraries (os, pathlib, json, sqlite3, datetime)"],
    ["9 Approach justification: ≥2 methods + baseline", "Sections 4.1–4.10: overlap baseline; TF-IDF, BM25; e5-small, e5-base, bge-m3; hybrid; quality, time, memory"],
    ["10 SQL: ER diagram, ≥8 queries, results to pandas", "Section 2.3: sql/schema.sql, sql/queries.sql (13 queries), docs/er_diagram.png, outputs/sql/"],
    ["11 Data volume, chunks, Parquet, dtypes", "952 MB CSV, 223,245 acts, 3.12 M passages; chunked read, Parquet 30 MB (Section 2.2)"],
    ["Topic 16: BM25 vs TF-IDF vs embeddings, Recall@k and MRR, ≥50 annotated queries", "Section 4.2: 53 needs, 159 queries; Success@k, Recall@50, MRR@10, nDCG@10"],
    ["Cluster 3: metadata audit; normalised schema; Kazakh preprocessing (word forms, suffix stemming, character n-grams); no leakage; error analysis; user input", "Sections 2.2, 2.3, 3.1, 2.6, 4.11 and the web application"],
], widths=[7.5, 9.1], size=8.5)
doc.add_heading("Appendix B. Reproduction", level=1)
body("Python 3.12, a CUDA GPU with 4 GB is enough. Install with pip install -r requirements.txt (PyTorch from the CUDA index). The numbered scripts in src/ are run in the order given in README.md; "
     "python src/00_download_data.py downloads and verifies the data (the real download path was not run in the final environment). python app/server.py starts the web application at http://localhost:8610; "
     "python -m pytest tests -q runs the unit tests and RUN_GOLDEN=1 python -m pytest tests/test_golden.py the behaviour tests on the real index. Large data files are not in the repository: data/ is rebuilt by the scripts.")
doc.add_heading("Appendix C. Team contributions", level=1)
body("The course requires each team member’s contribution to be stated. The repository history records the work of one author; the contributions of the other registered team members are not recorded in the project files and must be filled in by the team before submission:")
table("Contributions", ["Team member", "Contribution"], [
    ["Alisher Shayakhmetov", "[to be confirmed by the team] — in the repository: data acquisition and audit, linking, schema and SQL, chunking, test set and judgments, retrieval experiments, web application, tests, report"],
    ["Arsen Zhambekov", "[to be filled in by the team]"],
    ["Yernar Sakenov", "[to be filled in by the team]"],
], widths=[4.5, 12], size=9)

doc.save(str(OUT))
print("saved", OUT, "| tables", counter["t"], "| figures", counter["f"])
