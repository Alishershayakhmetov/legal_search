"""Recall@k curves for report/presentation v2 (from outputs/unified_comparison.json)."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = Path(__file__).resolve().parent / "figures"
rows = json.loads((ROOT / "outputs" / "unified_comparison.json").read_text(encoding="utf-8"))["rows"]
KS = (1, 5, 10, 20, 50)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8), sharey=True)
style = {"Keyword overlap": ("#bdbdbd", "--"), "TF-IDF": ("#8c8c8c", "-."), "BM25": ("#525252", "-"), "e5-small": ("#9ecae1", "-"), "e5-base": ("#4292c6", "-"), "bge-m3": ("#08519c", "-"), "Hybrid": ("#e6550d", ":")}
for ax, lang, suffix, title in ((axes[0], "ru", "stemming", "Russian queries"), (axes[1], "kk", "5-letter prefix", "Kazakh queries")):
    pick = {"Keyword overlap": f"Keyword overlap (baseline), {suffix}", "TF-IDF": f"TF-IDF, {suffix}", "BM25": f"BM25, {suffix}", "e5-small": "Dense e5-small", "e5-base": "Dense e5-base", "bge-m3": "Dense bge-m3", "Hybrid": "Hybrid BM25 + bge-m3 (RRF)"}
    for label, method in pick.items():
        r = next(x for x in rows if x["lang"] == lang and x["method"] == method)
        c, ls = style[label]
        ax.plot(range(len(KS)), [r[f"recall@{k}"] for k in KS], ls, color=c, marker="o", ms=3.5, lw=2 if label in ("BM25", "bge-m3") else 1.4, label=label)
    ax.set_xticks(range(len(KS))); ax.set_xticklabels([f"@{k}" for k in KS]); ax.set_title(title, fontsize=10); ax.set_ylim(0, 1); ax.grid(alpha=0.25)
axes[0].set_ylabel("Recall@k")
h, l = axes[1].get_legend_handles_labels()
fig.legend(h, l, frameon=False, fontsize=8.5, loc="lower center", ncol=7)
fig.tight_layout(rect=(0, 0.07, 1, 1)); fig.savefig(OUT / "fig_recall_curves.png", dpi=170); plt.close(fig)
print("ok")
