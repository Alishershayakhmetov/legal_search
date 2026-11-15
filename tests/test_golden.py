"""Regression guard: fixed questions must keep returning the same articles.

Loads the real engine (about a minute, needs the data and the GPU or a lot of patience on the CPU), so it runs only on request:
    RUN_GOLDEN=1 python -m pytest tests/test_golden.py -q
Regenerate the list after an intended change with src/38_make_golden.py and say why in the commit.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))

pytestmark = pytest.mark.skipif(os.environ.get("RUN_GOLDEN") != "1", reason="set RUN_GOLDEN=1 to run (loads the real index)")
GOLDEN = json.loads((ROOT / "annotation" / "golden_queries.json").read_text(encoding="utf-8")) if (ROOT / "annotation" / "golden_queries.json").exists() else []


@pytest.fixture(scope="module")
def engine():
    from engine import SearchEngine
    return SearchEngine()


@pytest.mark.parametrize("case", GOLDEN, ids=[g["id"] for g in GOLDEN])
def test_golden_query_returns_expected_article(engine, case):
    hits, _ = engine.search(case["query"], case["top"], "dense")
    found = [(h.title, h.article_no) for h in hits]
    assert (case["expect_title"], case["expect_article"]) in found, f"{case['query']!r} returned {found}"


def test_off_topic_questions_are_flagged_and_few_legal_ones_are(engine):
    off = json.loads((ROOT / "annotation" / "out_of_scope_queries.json").read_text(encoding="utf-8"))
    for lang in ("ru", "kk", "en"):
        flagged = sum(engine.search(q, 5, "dense")[1]["low_confidence"] for q in off[lang])
        assert flagged == len(off[lang]), (lang, flagged)
    wrongly = [c["query"] for c in GOLDEN if engine.search(c["query"], 5, "dense")[1]["low_confidence"]]
    assert len(wrongly) <= 3, wrongly  # the threshold keeps about 95% of in-scope questions by construction


def test_latin_typed_russian_finds_the_labour_code(engine):
    hits, info = engine.search("kak rastorgnut trudovoy dogovor po initsiative rabotodatelya", 8, "dense")
    assert info["lang"] == "ru" and any("Трудовой" in h.title for h in hits)


def test_evasion_question_gets_the_policy_note(engine):
    _, info = engine.search("Как скрыть доходы от налоговой?", 5, "dense")
    assert any("не подсказывает способов обойти" in n for n in info["notes"])
