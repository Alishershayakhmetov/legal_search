"""Charts for the report and the presentation, drawn from the result files (judgments v1)."""
import glob
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report" / "figures"
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
        ax.set_title({"ru": "русский запрос", "kk": "казахский запрос", "en": "английский запрос (напрямую)"}[lang], fontsize=10)
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
    ax.bar([i - 0.2 for i in x], art, 0.4, label="только статьи (319 тыс.)", color="#4292c6")
    ax.bar([i + 0.2 for i in x], full, 0.4, label="весь текст (1,7 млн)", color="#bdbdbd")
    for i, (a, f) in enumerate(zip(art, full)):
        ax.text(i - 0.2, a + 0.015, f"{a:.2f}", ha="center", fontsize=8)
        ax.text(i + 0.2, f + 0.015, f"{f:.2f}", ha="center", fontsize=8)
    ax.set_xticks(list(x)); ax.set_xticklabels(labels, fontsize=9); ax.set_ylim(0, 0.8); ax.set_ylabel("Success@10")
    ax.legend(frameon=False, fontsize=9)
    fig.tight_layout(); fig.savefig(OUT / "fig_scope.png", dpi=170); plt.close(fig)

    # 3. English strategies
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    names = ["напрямую\ne5-small", "напрямую\nbge-m3", "перевод +\nBM25", "перевод +\nсмысловой bge-m3", "перевод +\nгибрид bge-m3"]
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
    steps = [("Kazakh-\nLawCorpus\nCSV 952 МБ\n223 тыс. актов", "#deebf7"), ("Parquet\n+ SQLite\n13 таблиц, ER", "#deebf7"),
             ("Тексты\nMendeley\n204 тыс. файлов\n7,1 ГБ", "#fff2cc"), ("Связка\nфайл → акт\n79,8% / 81,1%", "#fff2cc"),
             ("Нарезка\n3,12 млн\nфрагментов", "#fff2cc"), ("Индексы\nBM25 и\nэмбеддинги", "#e2f0d9"), ("Поиск и\nприложение", "#e2f0d9")]
    w, gap = 1.38, 0.13
    for i, (t, c) in enumerate(steps):
        x0 = 0.1 + i * (w + gap)
        ax.add_patch(FancyBboxPatch((x0, 0.8), w, 1.3, boxstyle="round,pad=0.03", fc=c, ec="#555", lw=1))
        ax.text(x0 + w / 2, 1.45, t, ha="center", va="center", fontsize=8.5)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x0 + w + gap - 0.02, 1.45), xytext=(x0 + w + 0.02, 1.45), arrowprops=dict(arrowstyle="->", color="#555"))
    ax.text(0.1, 0.35, "Данные и метаданные", fontsize=8, color="#2f5597"); ax.text(3.2, 0.35, "Тексты и разметка", fontsize=8, color="#7f6000"); ax.text(7.7, 0.35, "Поиск", fontsize=8, color="#385723")
    fig.savefig(OUT / "fig_pipeline.png", dpi=170, bbox_inches="tight", pad_inches=0.1); plt.close(fig)
    print("figures:", sorted(p.name for p in OUT.glob("fig_*.png")))


if __name__ == "__main__":
    main()
