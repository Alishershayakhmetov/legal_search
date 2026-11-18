"""Applies the v2 corrections to build_report_v2.py (copy of the first English report builder)."""
from pathlib import Path

p = Path(__file__).with_name("build_report_v2.py")
t = p.read_text(encoding="utf-8")


def rep(a, b):
    global t
    assert t.count(a) == 1, a[:80]
    t = t.replace(a, b)


# paths and output
rep('ROOT = Path(__file__).resolve().parent.parent\nFIG = ROOT / "report" / "figures_en"\nOUT = ROOT / "report" / "Report_Kazakh_Legal_Search_Engine.docx"',
    'ROOT = Path(__file__).resolve().parent.parent.parent\nFIG = ROOT / "report" / "figures_en"\nFIG2 = ROOT / "report" / "v2" / "figures"\nOUT = ROOT / "report" / "v2" / "Report_Kazakh_Legal_Search_Engine_v2.docx"')

# 1.1 related work (inserted before section 2)
rep('# ------------------------------------------------------------------ 2 DATA', '''doc.add_heading("1.1 Related work and positioning", level=2)
body("Lexical ranking with BM25 [4] remains a strong baseline, and dense retrieval with learned embeddings has been shown to beat it on many question-answering collections [14]; zero-shot comparisons across domains show that the winner depends on the domain and that hybrids are often competitive [15]. "
     "Multilingual retrieval benchmarks such as MIRACL [16] cover 18 languages with native-speaker judgments, and for Kazakh there is KazQAD, an open-domain question answering dataset built on Kazakh Wikipedia and national exam questions [17]; neither is about legislation. "
     "Legal retrieval research is dominated by case-law retrieval (for example LeCaRD for Chinese criminal cases [18]) and by domain-specific language models such as LEGAL-BERT [19]. "
     "Statute retrieval for Kazakhstani law in three languages with article-level judgments, which this project addresses, was not found as a public benchmark. "
     "The official portal adilet.zan.kz offers search over the same legislation; we did not evaluate it (its pages are rendered with JavaScript and it disallows automated access), so no comparison with it is made. "
     "Our contribution is therefore an applied one: a reproducible pipeline from raw metadata and texts to a searchable index, a small judged test set, a controlled comparison of lexical and dense methods with significance tests, and the practical layers (filters, warnings, amendment history) needed to use the result.")

# ------------------------------------------------------------------ 2 DATA''')

# SQL row 13
rep('"8% / 52% / 40% (before the chunker fix)"', '"11.0% / 49.6% / 39.4% (articles / other / tables, recomputed after the chunker fix)"')

# title layer table with readable names
rep('rows = [[t["lang"], t["system"], f2(t["success@1"]), f2(t["success@5"]), f2(t["success@10"]), f3(t["mrr@10"])] for lang in ("ru", "kk", "en") for t in TITLE if t["lang"] == lang]',
    '''SYS_NAMES = {"bm25_word": "BM25, word forms", "bm25_p5": "BM25, 5-letter prefix", "bm25_stem": "BM25, stemming", "bm25_char": "BM25, character n-grams (3–5)", "dense": "Dense e5-small", "hybrid": "Hybrid BM25 + e5-small",
             "dense_cross": "Dense, English query direct", "bm25_translated": "BM25 on the translated query", "dense_translated": "Dense on the translated query", "hybrid_translated": "Hybrid on the translated query"}
LANG_NAMES = {"ru": "Russian", "kk": "Kazakh", "en": "English"}
rows = [[LANG_NAMES[t["lang"]], SYS_NAMES.get(t["system"], t["system"]), f2(t["success@1"]), f2(t["success@5"]), f2(t["success@10"]), f3(t["mrr@10"])] for lang in ("ru", "kk", "en") for t in TITLE if t["lang"] == lang]''')

# 4.9 split into four parts
a = t.index('doc.add_heading("4.9 Abbreviations, query router, amendments, act comparison", level=2)')
b = t.index('doc.add_heading("4.10 Cited answer from a local language model", level=2)')
t = t[:a] + '''doc.add_heading("4.9 Abbreviations, query router, amendments and act comparison", level=2)
ab = jload("abbreviations.json")
w_top1, e_top1 = sum(r["found_top1"] for r in ab if r["mode"] == "without"), sum(r["found_top1"] for r in ab if r["mode"] == "with")
router = jload("router.json")["accuracy"]["all"]
doc.add_heading("Abbreviations", level=3)
body(f"Upper-case abbreviations (ТК, ГК, УК, ОСМС, МРП and about twenty more) are spelled out before encoding. On 14 questions written with abbreviations the expected act is among the top five results with and without the expansion, "
     f"but it is the first result in {e_top1} cases instead of {w_top1} (5 better, none worse). This is a descriptive check on our own questions, not a judged measurement.")
doc.add_heading("Query router", level=3)
body(f"The automatic mode sends a short query whose best act title is closer than its best article to the act search, and everything else to the article search. On the 159 test queries (24 titles, 135 questions) the rule makes {router['n'] - router['correct']} errors, "
     "but the gap between the classes is thin (−0.013 for questions against +0.018 for titles) and the threshold was read from the same queries, so its accuracy on new queries is unconfirmed.")
doc.add_heading("Amendment history", level=3)
body(f"Footnotes of the form “Сноска. Статья 9 с изменениями, внесёнными законом РК от …” exist for {AMD['ru_with_footnote']:,} Russian and {AMD['kk_with_footnote']:,} Kazakh articles; {AMD['ru_footnote_parsed'] / AMD['ru_with_footnote']:.1%} and {AMD['kk_footnote_parsed'] / AMD['kk_with_footnote']:.1%} are parsed "
     f"into {AMD['entries']:,} entries (action, date, number, entry into force). Notes about changes not yet in force become warnings, because the texts are as of 01.04.2024. 34 random parses were read by hand and the errors found were fixed; an empty history does not mean an article was never changed.")
doc.add_heading("Comparison of acts", level=3)
body(f"The “compare acts” view shows the best article of each of five acts. The right act is among the five for {RGM['ru']['regimes_act']} of {RGM['ru']['n']} Russian and {RGM['kk']['regimes_act']} of {RGM['kk']['n']} Kazakh needs, "
     f"but the exact judged article among the best-per-act articles is found less often than in the plain top five ({RGM['ru']['regimes_article']} against {RGM['ru']['plain5']} in Russian), so the view complements the list and does not replace it.")
''' + t[b:]

# references
rep('"[13] Gemma Team. Gemma 3 Technical Report, arXiv:2503.19786, 2025 (the local model used for answers)."]',
    '''"[13] Gemma Team. Gemma 3 Technical Report, arXiv:2503.19786, 2025 (the local model used for answers).",
        "[14] V. Karpukhin et al. Dense Passage Retrieval for Open-Domain Question Answering. EMNLP 2020, arXiv:2004.04906.",
        "[15] N. Thakur et al. BEIR: A Heterogeneous Benchmark for Zero-shot Evaluation of Information Retrieval Models. NeurIPS Datasets and Benchmarks 2021, arXiv:2104.08663.",
        "[16] X. Zhang et al. MIRACL: A Multilingual Retrieval Dataset Covering 18 Diverse Languages. Transactions of the ACL 11, 2023, pp. 1114–1131, arXiv:2210.09984.",
        "[17] R. Yeshpanov, P. Efimov, L. Boytsov, A. Shalkarbayuli, P. Braslavski. KazQAD: Kazakh Open-Domain Question Answering Dataset. LREC-COLING 2024, arXiv:2404.04487.",
        "[18] Y. Ma, Y. Shao, Y. Wu, Y. Liu et al. LeCaRD: A Legal Case Retrieval Dataset for Chinese Law System. SIGIR 2021, pp. 2342–2348.",
        "[19] I. Chalkidis et al. LEGAL-BERT: The Muppets straight out of Law School. Findings of EMNLP 2020, arXiv:2010.02559."]''')

# evaluation settings note at the start of Results
rep('body("95% confidence intervals for MRR@10 are about ±0.1 with 45 needs per language, so differences of a few points are not evidence.")',
    '''body("95% confidence intervals for MRR@10 are about ±0.1 with 45 needs per language, so differences of a few points are not evidence. Two evaluation settings appear below and should not be confused: "
     "Sections 4.1–4.6 and 4.12 measure the retrieval methods themselves, without status filters, on the full article index; Section 4.7 onwards measures what a user of the application sees, with the application’s default filters "
     "(no repealed acts, bills or amending acts). The second setting gives higher numbers because old editions and bills with near-identical text no longer crowd the top.")''')

# recall curves + examples inside 4.2 (after the pooled paragraph)
rep('pr, pk = PAIRED["paired_success_at_10"]["ru"], PAIRED["paired_success_at_10"]["kk"]\ntable("Paired view of BM25 and bge-m3 by need',
    '''figure(FIG2 / "fig_recall_curves.png", "Recall@k of every method (45 article needs per language)", 15.5)
EX = json.loads((ROOT / "report" / "v2" / "examples.json").read_text(encoding="utf-8"))
doc.add_heading("Examples", level=3)
ex_rows = []
for e in EX:
    ex_rows.append([{"ru": "ru", "kk": "kk", "en": "en"}[e["lang"]] + ": " + e["query"][:90], "<br>".join(e["bm25"]).replace("<br>", chr(10)) if e["bm25"] else "— (no English text)", chr(10).join(e["dense"])])
table("Top three articles for sample questions (default filters; articles in Russian, act titles as in the corpus)", ["Question", "BM25", "bge-m3"], ex_rows, widths=[4.2, 6.2, 6.2], size=7.5)
body("The examples show the typical pattern. For the theft question BM25 ranks an unrelated civil-code article about warehouse storage first, while bge-m3 returns the Criminal Code articles on theft, robbery and piracy in the top three; "
     "for the VAT-rate question both find the Tax Code, and bge-m3 returns the article on rates first. For the appeal question in English, bge-m3 returns the Civil Procedure Code articles on appeal deadlines, although the corpus has no English text. "
     "For the dismissal question in Kazakh neither method puts the most relevant Labour Code article first, which matches the weak spots in Section 4.11.")
pr, pk = PAIRED["paired_success_at_10"]["ru"], PAIRED["paired_success_at_10"]["kk"]
table("Paired view of BM25 and bge-m3 by need''')

# 3.7 web application with screenshots (before section 4)
rep('# ------------------------------------------------------------------ 4 RESULTS', '''doc.add_heading("3.7 The web application and a user session", level=2)
body("The user types a question in Kazakh, Russian or English (or picks one of the 53 test questions in the examples panel). The page detects the language from the alphabet, the engine encodes the question with bge-m3, and the automatic mode chooses between act search and article search. "
     "Each result card shows the act, article number and heading, kind, year and status, the beginning of the article with deadlines (yellow) and amounts (green) highlighted, a collapsible amendment history, buttons for key sentences, thumbs up/down and a link to the act on adilet.zan.kz. "
     "The right-hand panel holds the method (semantic, BM25, hybrid), the number of results and the filters. The interface text is currently Russian; the search itself supports three languages and localisation of the interface is planned. Figures 6–8 show three typical sessions.")
figure(FIG2 / "app_search.png", "Article search: “Какое наказание грозит за кражу?” (What is the punishment for theft?) — the first card is Article 188 of the Criminal Code", 15)
figure(FIG2 / "app_regimes.png", "Compare acts: “Сколько дней отпуска положено?” (How many days of leave are due?) — one best article per act, with highlighted deadlines", 15)
figure(FIG2 / "app_offtopic.png", "Off-topic question “Как приготовить плов в казане?” (How to cook pilaf?) — the page warns that no reliable article was found", 15)

# ------------------------------------------------------------------ 4 RESULTS''')

# Appendix C: detailed contributions
a = t.index('doc.add_heading("Appendix C. Team contributions", level=1)')
b = t.index('doc.add_heading("Appendix D. Licence, languages and third-party works", level=1)')
t = t[:a] + '''doc.add_heading("Appendix C. Team contributions", level=1)
body("Roles are as stated by the team. The right-hand column maps each role to the parts of the project that belong to it; the repository history does not record who made which commit, so the mapping is by area of responsibility, not a per-commit attribution.")
table("Contributions", ["Team member", "Role (as stated)", "Project parts in this area"], [
    ["Alisher Shayakhmetov", "The “brain” of the project", "Retrieval methods (BM25, TF-IDF, dense models, hybrid, translation), evaluation protocol and statistics, ranking layers, robustness and abstention, answer generation and its checks, application back end (src/search_lib.py, evaluate.py, app/engine.py, answer.py, tests)"],
    ["Arsen Zhambekov", "Data collection", "Obtaining and checking the data sources (KazakhLawCorpus metadata, Mendeley texts, adilet.zan.kz as link-out) and the download and conversion scripts (src/00, src/01); the downstream audit, linking, SQL schema and chunking build on this data"],
    ["Yernar Sakenov", "Web site design; evaluation of the data and annotation", "Design of the web page (app/static/index.html), the annotation of needs and relevance judgments (annotation/needs.json, qrels_v1.json, review.html) and the review of the Kazakh queries"],
], widths=[3.4, 3.4, 9.8], size=8.5)
''' + t[b:]
p.write_text(t, encoding="utf-8")
print("patched")
