"""Applies the v2 corrections to build_slides_v2.py (copy of the first English presentation builder)."""
from pathlib import Path

p = Path(__file__).with_name("build_slides_v2.py")
t = p.read_text(encoding="utf-8")


def rep(a, b):
    global t
    assert t.count(a) == 1, a[:80]
    t = t.replace(a, b)


rep('ROOT = Path(__file__).resolve().parent.parent\nFIG = ROOT / "report" / "figures_en"\nOLD = ROOT / "report" / "figures"\nOUT = ROOT / "report" / "Presentation_Kazakh_Legal_Search_Engine.pptx"',
    'ROOT = Path(__file__).resolve().parent.parent.parent\nFIG = ROOT / "report" / "figures_en"\nFIG2 = ROOT / "report" / "v2" / "figures"\nOUT = ROOT / "report" / "v2" / "Presentation_Kazakh_Legal_Search_Engine_v2.pptx"')

# agenda + related work
rep("# 2 problem", '''# 1b agenda
s = new_slide("Agenda", "About 15 minutes: 12 for the talk, 3 for the demo and questions",
              "Order of the talk: the problem and related work, the data and how we prepared it, the methods and the evaluation, the results with their uncertainty, the application with a live demo, and the limits.")
table(s, 0.6, 1.9, 12.1, [["Part", "Slides", "Minutes"], ["Problem and related work", "3–4", "1.5"], ["Data: sources, audit, linking, chunking, test set", "5–9", "3"], ["Methods and evaluation", "10", "1"],
                          ["Results: retrieval, significance, scope, cost, ranking, robustness", "11–18", "4"], ["Application, examples, cited answer, errors", "19–22", "3"], ["Requirements, conclusions, team, credits", "23–26", "1.5"]],
      [7.6, 2.4, 2.1], size=17, row_h=0.62)

# 2 problem''')
rep("# 3 data", '''# 2b related work
s = new_slide("Related work and positioning", "What exists, and what this project adds",
              "BM25 is still a strong baseline and dense retrieval often beats it; benchmarks like BEIR show the winner depends on the domain. MIRACL covers eighteen languages and KazQAD is a Kazakh question answering set, but neither is about legislation. Legal retrieval research is mostly case law, for example LeCaRD for Chinese cases. We did not find a public benchmark for Kazakhstani statutes in three languages with article-level judgments, so our contribution is applied: a reproducible pipeline, a small judged set, a controlled comparison and the practical layers around it.")
bullets(s, 0.6, 1.8, 12.1, 5.0, [
    "Lexical vs dense|: BM25 (Robertson & Zaragoza 2009) vs dense retrieval (Karpukhin et al. 2020); no universal winner across domains (BEIR, Thakur et al. 2021).",
    "Multilingual and Kazakh|: MIRACL (18 languages, Zhang et al. 2023); KazQAD (Kazakh open-domain QA, Yeshpanov et al. 2024) — neither covers legislation.",
    "Legal|: mostly case-law retrieval (LeCaRD, Ma et al. 2021) and legal language models (LEGAL-BERT, Chalkidis et al. 2020).",
    "Gap|: no public statute-retrieval benchmark for Kazakhstani law in kk / ru / en with article-level judgments was found.",
    "Not compared|: the search of adilet.zan.kz (JavaScript pages, automated access disallowed).",
], size=18, gap=12)

# 3 data''')

# application slide with fresh screenshots
rep('s.shapes.add_picture(str(OLD / "app_ru_search.jpg"), Inches(0.5), Inches(1.6), width=Inches(7.2))',
    's.shapes.add_picture(str(FIG2 / "app_search.png"), Inches(0.5), Inches(1.55), width=Inches(5.5))\ns.shapes.add_picture(str(FIG2 / "app_regimes.png"), Inches(6.8), Inches(1.55), width=Inches(5.5))')
rep('bullets(s, 7.9, 1.7, 5.1, 5.2, ["Modes|: automatic, articles, act by title, compare acts, compare methods."', 'bullets(s, 0.6, 5.25, 12.1, 1.8, ["Modes|: automatic, articles, act by title, compare acts, compare methods."')
rep('size=14, gap=7)\n\n# 16 cited answer', 'size=12, gap=2)\n\n# 15b examples\nEXS = json.loads((ROOT / "report" / "v2" / "examples.json").read_text(encoding="utf-8"))\ns = new_slide("Examples: BM25 vs bge-m3", "Top-3 articles, default filters",\n              "Theft: BM25 puts an unrelated civil-code article about warehouse storage first; bge-m3 returns the criminal-code articles on theft, robbery and piracy. The English question about appeals returns the Civil Procedure Code articles although the corpus has no English text. For the Kazakh dismissal question neither method puts the best Labour Code article first.")\nrows = [["Question", "BM25 (top 1 / 2)", "bge-m3 (top 1 / 2)"]]\nfor e in (EXS[0], EXS[3], EXS[4]):\n    cut = lambda h: (lambda tt, art: tt.replace("Республики Казахстан", "РК").replace("О налогах и других обязательных платежах в бюджет (Налоговый кодекс)", "Налоговый кодекс")[:37].rstrip() + ", art. " + art)(*h.split(" — ")[0].partition(", art. ")[::2])\n    rows.append([e["query"][:60], "—  (no English text)" if not e["bm25"] else cut(e["bm25"][0]) + chr(10) + cut(e["bm25"][1]), cut(e["dense"][0]) + chr(10) + cut(e["dense"][1])])\ntable(s, 0.6, 1.9, 12.1, rows, [3.5, 4.3, 4.3], size=13, row_h=0.8)\nbullets(s, 0.6, 5.7, 12.1, 1.3, ["Theft|: BM25 first hit is a warehouse-storage article; bge-m3 first hit is Article 188 (Theft).", "English question|: answered from the Civil Procedure Code without translation."], size=15, gap=5)\n\n# 16 cited answer')

# requirements slide before conclusions
rep("# 18 conclusions", '''# 17b requirements
s = new_slide("Course requirements: where they are met", "Details in Appendix A of the report",
              "A short checklist of the course requirements and where each is satisfied in the project and the report.")
table(s, 0.6, 1.8, 12.1, [["Requirement", "Where"], ["Python modules, functions, lists/dicts, files, try/except", "src/ and app/ (about 50 numbered scripts, libraries, tests)"],
                          ["User interface", "web mini-dashboard with filters (app/); no console menu"], ["≥2 methods + baseline; quality, time, memory", "keyword baseline, TF-IDF, BM25, 3 encoders, hybrid; slides 11–16"],
                          ["SQL: ER diagram, ≥8 queries, results to pandas", "13 queries, 13 tables, ER diagram (slide 6)"], ["Data volume, chunked read, Parquet", "952 MB CSV → 30 MB Parquet; 3.12 M passages (slides 5, 16)"],
                          ["BM25 vs TF-IDF vs embeddings; Recall@k, MRR; ≥50 queries", "53 needs / 159 queries; slides 11, 14"], ["Metadata audit, Kazakh preprocessing, no leakage, error analysis, user input", "slides 6, 10, 9, 22, 19"]],
      [6.2, 5.9], size=14, row_h=0.6)

# 18 conclusions''')

# team slide: detailed, then credits
a = t.index("# 19 team & next")
b = t.index("prs.save(str(OUT))")
t = t[:a] + '''# 19 team & next
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
textbox(s, 0.9, 0.7, 11.5, 0.9, "Team contributions and next steps", size=34, bold=True, color=RGBColor(255, 255, 255))
bullets(s, 0.9, 1.8, 11.5, 5.0, ["Alisher Shayakhmetov|: the “brain” — retrieval methods and models, evaluation and statistics, ranking layers, robustness, answer logic, application back end.",
                                 "Arsen Zhambekov|: data collection — obtaining and checking the sources, download and conversion scripts.",
                                 "Yernar Sakenov|: web site design; evaluation of the data and annotation — needs, judgments, review of the Kazakh queries.",
                                 "Next|: independent review of the judgments and a held-out question set; bge-m3 over all passages; evaluation of the answer with a stronger model; interface in three languages.",
                                 "Mapping|: roles as stated by the team; the repository does not record per-member commits."], size=18, gap=12)
for sh in s.shapes:
    if sh.has_text_frame:
        for para in sh.text_frame.paragraphs:
            for r in para.runs:
                r.font.color.rgb = RGBColor(255, 255, 255)
s.notes_slide.notes_text_frame.text = "Contributions as stated by the team; the mapping to project parts is by area of responsibility."

# 20 credits
s = new_slide("Licence and credits", "Code: MIT. Everything we used is credited with links in CREDITS.md",
              "The code is released under the MIT licence. Datasets: KazakhLawCorpus under Apache 2.0 and the Mendeley texts under CC BY 4.0. Models: bge-m3 and e5 under MIT; NLLB is non-commercial; Gemma has its own terms. Full list with links and licences is in CREDITS.md in the repository.")
table(s, 0.6, 1.8, 12.1, [["Work", "Licence", "Use"], ["KazakhLawCorpus (Tleubayeva et al., Data 2026) — Hugging Face", "Apache-2.0", "act metadata"],
                          ["Textual Foundations of Justice (Akhmetov, Zhamankhan, Zhetesov, Kubaeva), Mendeley Data", "CC BY 4.0", "full texts"], ["BAAI/bge-m3; intfloat/multilingual-e5", "MIT", "retrievers"],
                          ["bge-reranker-v2-m3; Qwen3-Embedding-0.6B", "Apache-2.0", "experiments"], ["NLLB-200 distilled 600M (Meta)", "CC BY-NC 4.0", "translation (non-commercial)"],
                          ["Gemma 3 4B via Ollama", "Gemma Terms", "optional local answers"], ["PyTorch, sentence-transformers, pandas, scikit-learn, NLTK, SQLite …", "BSD / Apache / MIT", "software"]],
      [7.0, 2.4, 2.7], size=13, row_h=0.55)
textbox(s, 0.6, 6.0, 12.1, 0.8, "Papers: BM25 (Robertson, Zaragoza 2009); BGE M3 (Chen et al. 2024); E5 (Wang et al. 2024); NLLB (2022); RRF (Cormack et al. 2009); DPR (Karpukhin 2020); BEIR (Thakur 2021); MIRACL (Zhang 2023); KazQAD (Yeshpanov 2024). Code: github.com/Alishershayakhmetov/legal_search", size=12, color=GREY)

# timing notes: seconds per slide for a 12-minute talk
secs = [20, 30, 45, 45, 40, 40, 45, 40, 40, 35, 40, 45, 40, 40, 35, 35, 40, 40, 60, 40, 40, 35, 30, 40, 40, 20]
for i, sl in enumerate(prs.slides):
    old = sl.notes_slide.notes_text_frame.text
    sl.notes_slide.notes_text_frame.text = f"[About {secs[i] if i < len(secs) else 30} s] " + old

''' + t[b:]
p.write_text(t, encoding="utf-8")
print("patched")
