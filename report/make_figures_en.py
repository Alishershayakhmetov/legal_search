"""Charts for the report and the presentation, drawn from the result files (judgments v1)."""
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report" / "figures_en"
OUT.mkdir(exist_ok=True)
COL = {"BM25": "#8c8c8c", "e5-small": "#9ecae1", "e5-base": "#4292c6", "bge-m3": "#08519c"}


def load(pattern):
    rows = []
    for p in sorted(glob.glob(str(ROOT / "outputs" / pattern))):
        rows += json.loads(Path(p).read_text(encoding="utf-8"))
    return rows


def get(rows, **kw):
    return next(r for r in rows if all(r.get(k) == v for k, v in kw.items()))


def main():
    sparse = load("sparse_results_articles_rukk_wordp5stem_v1_c2.json")
    dense = load("dense_results_*_articles_v1_c2.json")
    all_dense = load("dense_results_multilingual-e5-small_all_v1_c2.json")
    all_sparse = load("sparse_results_all_*_v1_c2.json")
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})

    # 1. Success@10 by system and language
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.6), sharey=True)
    for ax, lang, bm_mode in zip(axes, ("ru", "kk", "en"), ("stem", "p5", None)):
        names, vals, cols = [], [], []
        if bm_mode:
            names.append("BM25"); vals.append(get(sparse, lang=lang, analyzer=bm_mode, scheme="bm25")["success@10"]); cols.append(COL["BM25"])
        for model, label in (("multilingual-e5-small", "e5-small"), ("multilingual-e5-base", "e5-base"), ("bge-m3", "bge-m3")):
            system = "dense_cross" if lang == "en" else "dense"
            names.append(label); vals.append(get(dense, model=model, lang=lang, system=system)["success@10"]); cols.append(COL[label])
        bars = ax.bar(names, vals, color=cols)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center", fontsize=9)
        ax.set_title({"ru": "Russian queries", "kk": "Kazakh queries", "en": "English queries (direct)"}[lang], fontsize=10)
        ax.set_ylim(0, 1)
    axes[0].set_ylabel("Success@10")
    fig.tight_layout()
    fig.savefig(OUT / "fig_success10.png", dpi=170)
    plt.close(fig)

    # 2. corpus scope effect
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    labels, art, full = [], [], []
    for lang, mode in (("ru", "stem"), ("kk", "p5")):
        labels.append(f"BM25, {lang}")
        art.append(get(sparse, lang=lang, analyzer=mode, scheme="bm25")["success@10"])
        full.append(get(all_sparse, lang=lang, analyzer=mode, scheme="bm25")["success@10"])
        labels.append(f"e5-small, {lang}")
        art.append(get(dense, model="multilingual-e5-small", lang=lang, system="dense")["success@10"])
        full.append(get(all_dense, lang=lang, system="dense")["success@10"])
    x = range(len(labels))
    ax.bar([i - 0.2 for i in x], art, 0.4, label="articles only (319k)", color="#4292c6")
    ax.bar([i + 0.2 for i in x], full, 0.4, label="all text (1.7M)", color="#bdbdbd")
    for i, (a, f) in enumerate(zip(art, full)):
        ax.text(i - 0.2, a + 0.015, f"{a:.2f}", ha="center", fontsize=8)
        ax.text(i + 0.2, f + 0.015, f"{f:.2f}", ha="center", fontsize=8)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9); ax.set_ylim(0, 0.8); ax.set_ylabel("Success@10")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "fig_scope.png", dpi=170); plt.close(fig)

    # 3. English strategies
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    names = ["direct\ne5-small", "direct\nbge-m3", "translate +\nBM25", "translate +\ndense bge-m3", "translate +\nhybrid bge-m3"]
    vals = [get(dense, model="multilingual-e5-small", lang="en", system="dense_cross")["success@10"],
            get(dense, model="bge-m3", lang="en", system="dense_cross")["success@10"],
            get(dense, model="bge-m3", lang="en", system="bm25_translated")["success@10"],
            get(dense, model="bge-m3", lang="en", system="dense_translated")["success@10"],
            get(dense, model="bge-m3", lang="en", system="hybrid_translated")["success@10"]]
    bars = ax.bar(names, vals, color=["#9ecae1", "#08519c", "#8c8c8c", "#6baed6", "#3182bd"])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.2f}", ha="center", fontsize=9)
    ax.set_ylim(0, 1); ax.set_ylabel("Success@10"); ax.tick_params(axis="x", labelsize=8)
    fig.tight_layout(); fig.savefig(OUT / "fig_english.png", dpi=170); plt.close(fig)

    # 4. pipeline
    fig, ax = plt.subplots(figsize=(11, 2.9))
    ax.axis("off"); ax.set_xlim(0, 11); ax.set_ylim(0, 2.9)
    steps = [("Kazakh-\nLawCorpus\nCSV 952 MB\n223k acts", "#deebf7"), ("Parquet\n+ SQLite\n13 tables, ER", "#deebf7"),
             ("Mendeley\ntexts\n204k files\n7.1 GB", "#fff2cc"), ("Link\nfile → act\n79.8% / 81.1%", "#fff2cc"),
             ("Chunking\n3.12M\npassages", "#fff2cc"), ("BM25 and\nembedding\nindexes", "#e2f0d9"), ("Search and\nweb app", "#e2f0d9")]
    w, gap = 1.38, 0.13
    for i, (t, c) in enumerate(steps):
        x0 = 0.1 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x0, 0.8), w, 1.3, boxstyle="round,pad=0.03", fc=c, ec="#555", lw=1))
        ax.text(x0 + w / 2, 1.45, t, ha="center", va="center", fontsize=8.5)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x0 + w + gap - 0.02, 1.45), xytext=(x0 + w + 0.02, 1.45), arrowprops=dict(arrowstyle="->", color="#555"))
    ax.text(0.1, 0.35, "Data and metadata", fontsize=8, color="#2f5597"); ax.text(3.2, 0.35, "Texts and annotation", fontsize=8, color="#7f6000"); ax.text(7.7, 0.35, "Search", fontsize=8, color="#385723")
    fig.savefig(OUT / "fig_pipeline.png", dpi=170, bbox_inches="tight", pad_inches=0.1); plt.close(fig)
    print("figures:", sorted(p.name for p in OUT.glob("fig_*.png")))


if __name__ == "__main__":
    main()
