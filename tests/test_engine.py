import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from engine import Filters, build_mask, detect_language, group_rows, log_feedback, rrf  # noqa: E402


def table():
    return pd.DataFrame({
        "family": ["a", "a", "b", "c", "d", "e"],
        "article_no": ["1", "1", "2", "3", "4", "5"],
        "lang": ["ru", "kk", "ru", "ru", "ru", "ru"],
        "is_repealed": [0, 0, 1, 0, np.nan, 0],
        "linked": [True, True, True, True, False, True],
        "is_draft": [False, False, False, True, False, False],
        "is_amending": [False, False, False, False, False, True],
        "kind": ["Кодекс", "Кодекс", "Закон", "Закон", "Другое", "Закон"],
        "adopted_year": [2015, 2015, 1999, 2020, np.nan, 2010],
    })


def test_language_detection():
    assert detect_language("Сколько дней отпуска положено?") == "ru"
    assert detect_language("Жылына қанша күн демалыс беріледі?") == "kk"
    assert detect_language("How many days of leave am I entitled to?") == "en"
    assert detect_language("123 ???") == "ru"


def test_default_filters_hide_repealed_drafts_and_amending_acts():
    m = build_mask(table(), Filters())
    assert m.tolist() == [True, True, False, False, True, False]


def test_filters_can_be_relaxed_and_narrowed():
    df = table()
    assert build_mask(df, Filters(only_in_force=False, hide_drafts=False, hide_amending=False)).all()
    assert build_mask(df, Filters(include_unlinked=False)).tolist() == [True, True, False, False, False, False]
    assert build_mask(df, Filters(kinds=("Кодекс",))).tolist() == [True, True, False, False, False, False]
    assert build_mask(df, Filters(year_from=2012, year_to=2016)).tolist()[:2] == [True, True]


def test_grouping_merges_language_twins_and_keeps_order():
    df = table()
    out = group_rows(df, [1, 0, 2, 3], [0.9, 0.8, 0.7, 0.6], None, limit=3)
    assert [k for k, _, _ in out] == [("a", "1"), ("b", "2"), ("c", "3")]
    assert out[0][1] == 1  # the best-scoring twin is the representative


def test_rrf_rewards_agreement():
    order, score = rrf([[1, 2, 3], [3, 1, 4]])
    assert order[:2] == [1, 3]
    assert score[1] > score[2]


def test_feedback_is_appended(tmp_path):
    p = tmp_path / "fb.jsonl"
    assert log_feedback("q", "article", ("fam", "5"), "up", path=p)
    assert log_feedback("q2", "article", ("fam", "6"), "down", path=p)
    assert len(p.read_text(encoding="utf-8").strip().splitlines()) == 2


def test_article_reference_is_split_into_number_and_act_words():
    from engine import parse_reference
    assert parse_reference("статья 1 конституции рк") == ("1", "конституции")
    assert parse_reference("ст. 52 ТК РК") == ("52", "Трудовой кодекс")
    assert parse_reference("52 статья трудового кодекса") == ("52", "трудового кодекса")
    assert parse_reference("Қазақстан Республикасының Конституциясының 1-бабы") == ("1", "Конституциясының")
    assert parse_reference("article 1 of the constitution of Kazakhstan") == ("1", "constitution")
    assert parse_reference("статья 188 УК") == ("188", "Уголовный кодекс")


def test_questions_without_an_article_number_are_not_references():
    from engine import parse_reference
    assert parse_reference("сколько дней отпуска положено") is None
    assert parse_reference("статья 5") is None


def test_feedback_stores_the_question_only_with_consent(tmp_path):
    import json
    p = tmp_path / "fb.jsonl"
    log_feedback("Сколько дней отпуска?", "article", ("Закон", "5"), "up", path=p)
    log_feedback("Сколько дней отпуска?", "article", ("Закон", "5"), "up", path=p, keep_query=True)
    private, kept = [json.loads(line) for line in p.read_text(encoding="utf-8").splitlines()]
    assert "query" not in private and len(private["query_hash"]) == 12 and private["lang"] == "ru"
    assert kept["query"] == "Сколько дней отпуска?" and "query_hash" not in kept


def test_metadata_corrections_for_constitution_and_amending_titles():
    from engine import tidy_metadata
    df = pd.DataFrame({"display_title": ["Конституция Республики Казахстан", 'Закон Республики Казахстан "О внесении изменений и дополнений в Кодекс"',
                                         "Трудовой кодекс Республики Казахстан", "Республикасының Конституциясы"],
                       "kind": ["Другое", "Закон", "Кодекс", "Другое"], "is_amending": [False, False, False, np.nan]})
    tidy_metadata(df, "display_title")
    assert df.kind.tolist() == ["Конституция", "Закон", "Кодекс", "Другое"]
    assert df.is_amending.tolist() == [False, True, False, False]


def test_latin_typed_russian_is_read_back_into_cyrillic():
    from engine import latin_to_cyrillic
    assert latin_to_cyrillic("kak poluchit alimenty") == "как получит алименты"
    assert latin_to_cyrillic("Shtraf za kuri") == "штраф за кури"
    assert latin_to_cyrillic("№ 5, 2020") == "№ 5, 2020"


def test_policy_notice_only_for_questions_about_evading_the_law():
    from engine import policy_notice
    assert policy_notice("Как обойти налог на имущество?")
    assert policy_notice("как скрыть доходы от налоговой")
    assert policy_notice("How can I evade taxes in Kazakhstan?")
    assert policy_notice("Салықтан жалтару жолдары қандай?")
    assert policy_notice("Какая ответственность за уклонение от уплаты налогов?") is None
    assert policy_notice("Сколько дней отпуска положено?") is None


def test_confidence_thresholds_cover_every_language():
    from engine import CONFIDENCE_MIN
    assert set(CONFIDENCE_MIN) == {"ru", "kk", "en"} and all(0.4 < v < 0.8 for v in CONFIDENCE_MIN.values())
