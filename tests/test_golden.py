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
