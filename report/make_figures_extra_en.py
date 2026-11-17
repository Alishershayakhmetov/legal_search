"""Extra English charts: ranking variants, robustness, answer checks (from outputs/*.json)."""
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "report" / "figures_en"
OUT.mkdir(exist_ok=True)
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def main():
    rank = json.loads((ROOT / "outputs" / "rank_experiments.json").read_text(encoding="utf-8"))
    rv = {(r["lang"], r["variant"]): r for r in rank["summary"]}
    variants = [("base", "plain bge-m3"), ("instr_ru", "+ query instruction"), ("filters", "+ default filters"), ("filters+force_0.02", "+ filters + legal-force prior"), ("filters+rr_title", "+ filters + re-ranker")]
    fig, ax = plt.subplots(figsize=(8.6, 3.6))
    colors = ["#9ecae1", "#bdbdbd", "#4292c6", "#08519c", "#6baed6"]
    w = 0.16
    for i, ((key, label), c) in enumerate(zip(variants, colors)):
        vals = [rv[(lang, key)]["mrr@10"] for lang in ("ru", "kk", "en")]
        bars = ax.bar([j + (i - 2) * w for j in range(3)], vals, w, label=label, color=c)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}", ha="center", fontsize=7)
    ax.set_xticks(range(3)); ax.set_xticklabels(["Russian", "Kazakh", "English"]); ax.set_ylabel("MRR@10"); ax.set_ylim(0, 0.9)
    ax.legend(frameon=False, fontsize=8, ncol=2)
    fig.tight_layout(); fig.savefig(OUT / "fig_ranking.png", dpi=170); plt.close(fig)

    rob = json.loads((ROOT / "outputs" / "robustness.json").read_text(encoding="utf-8"))["summary"]
    rb = {(r["mode"], r["lang"], r["variant"]): r for r in rob}
    names = [("clean", "original"), ("typo_light", "light typos"), ("typo_heavy", "heavy typos"), ("nopunct", "no punctuation"), ("keywords", "4 keywords"), ("translit", "Latin letters")]
    fig, ax = plt.subplots(figsize=(8.6, 3.4))
    w = 0.26
    for i, (lang, label, c) in enumerate((("ru", "Russian", "#08519c"), ("kk", "Kazakh", "#6baed6"), ("en", "English", "#bdbdbd"))):
        vals = []
        for key, _ in names:
            r = rb.get(("plain", lang, key))
            vals.append(r["s10"] if r else 0)
        bars = ax.bar([j + (i - 1) * w for j in range(len(names))], vals, w, label=label, color=c)
        for j, (b, v) in enumerate(zip(bars, vals)):
            if rb.get(("plain", lang, names[j][0])):
                ax.text(b.get_x() + b.get_width() / 2, v + 0.01, f"{v:.2f}", ha="center", fontsize=7)
    fx = rb[("fixed", "ru", "translit")]["s10"]
    ax.annotate(f"with back-transliteration: {fx:.2f}", xy=(5 - w, rb[("plain", "ru", "translit")]["s10"]), xytext=(3.6, 1.0), fontsize=8, arrowprops=dict(arrowstyle="->", color="#555"))
    ax.set_xticks(range(len(names))); ax.set_xticklabels([n for _, n in names], fontsize=9); ax.set_ylabel("Success@10"); ax.set_ylim(0, 1.1)
    ax.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    fig.tight_layout(); fig.savefig(OUT / "fig_robustness.png", dpi=170); plt.close(fig)
    print("extra figures written")


if __name__ == "__main__":
    main()
