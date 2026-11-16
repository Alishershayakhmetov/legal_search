import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

import answer as A  # noqa: E402

EXCERPTS = [
    {"n": 1, "title": "Трудовой кодекс", "article_no": "87", "heading": "Отпуск", "text": "Статья 87. Отпуск\nОтпуск предоставляется не менее двадцати четырех календарных дней в году."},
    {"n": 2, "title": "О службе", "article_no": "73", "heading": "Отпуск", "text": "Статья 73. Отпуск\nСотрудникам предоставляется отпуск тридцать календарных дней."},
]


def fake_embed(texts):
    """Bag-of-letters vectors: similar strings are close, unrelated ones are not."""
    out = np.zeros((len(texts), 33), dtype=np.float32)
    for i, t in enumerate(texts):
        for ch in t.lower():
            if "а" <= ch <= "я":
                out[i, ord(ch) - ord("а")] += 1
    return out / np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)


class FakeBackend:
    name, model = "fake", "m"

    def __init__(self, text):
        self.text = text

    def complete(self, system, user, **kw):
        return self.text


def test_spelled_out_and_digit_numbers_match():
    assert 24 in A.numbers_in("не менее двадцати четырех календарных дней") and 24 in A.numbers_in("24 дня")
    assert 24 in A.numbers_in("жиырма төрт күн") and 1 not in A.numbers_in("одного из них")


def test_supported_sentence_is_kept_and_invented_number_or_citation_is_dropped():
    raw = ("Работнику предоставляется отпуск не менее 24 календарных дней в году [1]. "
           "Работнику предоставляется отпуск 45 календарных дней в году [1]. "
           "Сотрудникам предоставляется отпуск тридцать календарных дней [3]. "
           "Сотрудникам предоставляется отпуск тридцать календарных дней.")
    res = A.make_answer("отпуск", "ru", EXCERPTS, FakeBackend(raw), fake_embed, tau=0.3)
    ok = [s["ok"] for s in res["sentences"]]
    assert ok == [True, False, False, False] and res["status"] == "ok" and res["kept"] == 1 and res["dropped"] == 3
    reasons = [s["reasons"] for s in res["sentences"]]
    assert any("45" in r for r in reasons[1]) and "ссылка на несуществующую выдержку" in reasons[2] and "нет ссылки на выдержку" in reasons[3]


def test_abstention_and_fully_rejected_answers_are_reported():
    assert A.make_answer("q", "ru", EXCERPTS, FakeBackend("НЕТ ОТВЕТА. Выдержки не содержат."), fake_embed)["status"] == "abstain"
    res = A.make_answer("q", "ru", EXCERPTS, FakeBackend("Выдуманный факт про 99 дней [1]."), fake_embed, tau=0.3)
    assert res["status"] == "unverified" and res["kept"] == 0


def test_semantic_check_rejects_a_sentence_that_cites_an_unrelated_excerpt():
    raw = "Сотрудникам предоставляется отпуск тридцать календарных дней [1]."  # the words of excerpt 2, cited as excerpt 1
    strict = A.make_answer("q", "ru", EXCERPTS, FakeBackend(raw), fake_embed, tau=0.99)
    assert strict["sentences"][0]["ok"] is False and any("смысл не подтверждён" in r for r in strict["sentences"][0]["reasons"])


def test_backend_selection_and_missing_key(monkeypatch):
    import pytest

    import llm
    monkeypatch.setenv("LLM_BACKEND", "ollama")
    assert llm.get_backend().name == "ollama"
    monkeypatch.setenv("LLM_BACKEND", "anthropic")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(llm.LLMError):
        llm.get_backend()
    monkeypatch.setenv("LLM_BACKEND", "nonsense")
    with pytest.raises(llm.LLMError):
        llm.get_backend()
