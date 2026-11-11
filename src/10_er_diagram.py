from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs"

TABLES = {
    "act": [("law_id", "TEXT", "PK"), ("adopted_date", "TEXT", ""), ("adopted_year", "INTEGER", ""), ("published_date", "TEXT", ""),
            ("force_id", "INTEGER", "FK"), ("region_id", "INTEGER", "FK"), ("section_id", "INTEGER", "FK"),
            ("is_repealed", "INTEGER", ""), ("adilet_url", "TEXT", "")],
    "act_title": [("law_id", "TEXT", "PK,FK"), ("lang", "TEXT", "PK"), ("title", "TEXT", ""), ("is_placeholder", "INTEGER", "")],
    "text_file": [("file_id", "INTEGER", "PK"), ("law_id", "TEXT", "FK"), ("lang", "TEXT", ""), ("rel_path", "TEXT", ""),
                  ("size_bytes", "INTEGER", ""), ("match_type", "TEXT", ""), ("n_candidates", "INTEGER", ""), ("match_score", "REAL", "")],
    "passage": [("chunk_id", "INTEGER", "PK"), ("file_id", "INTEGER", "FK"), ("ord", "INTEGER", ""), ("article_no", "TEXT", ""),
                ("heading", "TEXT", ""), ("section", "TEXT", ""), ("n_chars", "INTEGER", ""), ("is_table", "INTEGER", ""),
                ("text_hash", "TEXT", "")],
    "legal_force": [("force_id", "INTEGER", "PK"), ("name", "TEXT", "")],
    "region": [("region_id", "INTEGER", "PK"), ("name", "TEXT", "")],
    "db_section": [("section_id", "INTEGER", "PK"), ("name", "TEXT", "")],
    "act_form": [("law_id", "TEXT", "PK,FK"), ("form_id", "INTEGER", "PK,FK")],
    "act_area": [("law_id", "TEXT", "PK,FK"), ("area_id", "INTEGER", "PK,FK")],
    "act_body": [("law_id", "TEXT", "PK,FK"), ("body_id", "INTEGER", "PK,FK")],
    "form": [("form_id", "INTEGER", "PK"), ("name", "TEXT", "")],
    "legal_area": [("area_id", "INTEGER", "PK"), ("name", "TEXT", "")],
    "body": [("body_id", "INTEGER", "PK"), ("name", "TEXT", "")],
}

# (parent, child, mermaid label, parent side, parent frac, child side, child frac); every relationship is one parent to many children
RELATIONS = [
    ("legal_force", "act", "classifies", "bottom", 0.5, "top", 0.2),
    ("region", "act", "locates", "bottom", 0.5, "top", 0.5),
    ("db_section", "act", "groups", "bottom", 0.5, "top", 0.8),
    ("act", "act_title", "has", "left", 0.2, "right", 0.5),
    ("act", "text_file", "has text", "left", 0.8, "right", 0.3),
    ("text_file", "passage", "split into", "right", 0.7, "left", 0.3),
    ("act", "act_form", "has", "right", 0.2, "left", 0.5),
    ("form", "act_form", "used by", "left", 0.5, "right", 0.5),
    ("act", "act_area", "has", "right", 0.5, "left", 0.5),
    ("legal_area", "act_area", "used by", "left", 0.5, "right", 0.5),
    ("act", "act_body", "has", "right", 0.8, "left", 0.5),
    ("body", "act_body", "used by", "left", 0.5, "right", 0.5),
]

# top-left corner (x, y) and width in diagram units, y grows upward
LAYOUT = {
    "act": (8.5, 10.0, 4.4), "passage": (7.6, 3.6, 4.4),
    "act_title": (2.0, 10.0, 4.3), "text_file": (2.0, 4.2, 4.3),
    "legal_force": (5.6, 14.6, 3.2), "region": (9.4, 14.6, 3.2), "db_section": (13.2, 14.6, 3.2),
    "act_form": (15.0, 9.4, 3.2), "act_area": (15.0, 6.6, 3.2), "act_body": (15.0, 3.8, 3.2),
    "form": (19.4, 9.4, 3.0), "legal_area": (19.4, 6.6, 3.0), "body": (19.4, 3.8, 3.0),
}
ROW = 0.5


def box(name):
    x, y, w = LAYOUT[name]
    h = ROW * (len(TABLES[name]) + 1)
    return x, y, w, h


def anchor(name, side, frac=0.5):
    x, y, w, h = box(name)
    return {"left": (x, y - h * frac), "right": (x + w, y - h * frac), "top": (x + w * frac, y), "bottom": (x + w * frac, y - h)}[side]


def draw_png(path):
    fig, ax = plt.subplots(figsize=(16, 11))
    ax.set_xlim(1, 23.2)
    ax.set_ylim(-2.0, 16.4)
    ax.axis("off")
    for parent, child, _, ps, pf, cs, cf in RELATIONS:
        (x1, y1), (x2, y2) = anchor(parent, ps, pf), anchor(child, cs, cf)
        ax.plot([x1, x2], [y1, y2], color="#555", lw=1.3, zorder=1)
        ax.text(x1 + (x2 - x1) * 0.12, y1 + (y2 - y1) * 0.12 + 0.12, "1", fontsize=10, color="#222", ha="center", zorder=4)
        ax.text(x1 + (x2 - x1) * 0.88, y1 + (y2 - y1) * 0.88 + 0.12, "N", fontsize=10, color="#222", ha="center", zorder=4)
    for name, cols in TABLES.items():
        x, y, w, h = box(name)
        link = name.startswith("act_") and name != "act_title"
        head = "#c7d2fe" if name == "act" else ("#fde68a" if link else "#d1fae5")
        ax.add_patch(Rectangle((x, y - h), w, h, facecolor="white", edgecolor="#333", lw=1.4, zorder=2))
        ax.add_patch(Rectangle((x, y - ROW), w, ROW, facecolor=head, edgecolor="#333", lw=1.4, zorder=3))
        ax.text(x + w / 2, y - ROW / 2, name, ha="center", va="center", fontsize=11, fontweight="bold", zorder=4)
        for i, (col, typ, flag) in enumerate(cols):
            cy = y - ROW * (i + 1.5)
            weight = "bold" if "PK" in flag else "normal"
            style = "italic" if "FK" in flag else "normal"
            ax.text(x + 0.12, cy, col, fontsize=9, family="monospace", va="center", fontweight=weight, fontstyle=style, zorder=4)
            ax.text(x + w - 0.12, cy, (flag + " " if flag else "") + typ.lower(), fontsize=8, family="monospace", va="center",
                    ha="right", color="#555", zorder=4)
    ax.text(1.2, 16.2, "KazakhLawCorpus: normalized SQLite schema", fontsize=14, fontweight="bold", va="top")
    ax.text(1.2, 15.6, "blue: core act, green: dimensions/titles, yellow: many-to-many links; bold = PK, italic = FK", fontsize=9, va="top", color="#444")
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


def mermaid():
    lines = ["erDiagram"]
    for parent, child, label, *_ in RELATIONS:
        lines.append(f'    {parent} ||--o{{ {child} : "{label}"')
    for name, cols in TABLES.items():
        lines.append(f"    {name} {{")
        for col, typ, flag in cols:
            lines.append(f"        {typ} {col}" + (f" {flag.replace(',', ',')}" if flag else ""))
        lines.append("    }")
    return "\n".join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    draw_png(OUT / "er_diagram.png")
    (OUT / "er_diagram.md").write_text("# ER diagram\n\n![ER diagram](er_diagram.png)\n\n```mermaid\n" + mermaid() + "\n```\n", encoding="utf-8")
    print("saved", OUT / "er_diagram.png", OUT / "er_diagram.md")


if __name__ == "__main__":
    main()
