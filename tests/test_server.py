import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from engine import Hit  # noqa: E402
from server import hit_to_dict, make_filters  # noqa: E402


def hit(**kw):
    base = dict(title="Закон", article_no="5", heading="Заголовок", section="", kind="Закон", year=2015, in_force=True, url="u", law_id="L", score=1.0,
                matched_lang="ru", texts={"ru": "Статья 5. Заголовок\nТекст статьи.", "kk": "5-бап. Тақырып\nБап мәтіні."}, headings={"ru": "Заголовок", "kk": "Тақырып"})
    base.update(kw)
    return Hit(**base)


def test_card_uses_the_language_of_the_question_and_drops_the_heading_line():
    ru = hit_to_dict(hit(), "ru")
    kk = hit_to_dict(hit(), "kk")
    assert ru["snippet"] == "Текст статьи." and ru["heading"] == "Заголовок"
    assert kk["snippet"] == "Бап мәтіні." and kk["heading"] == "Тақырып"


def test_long_text_is_cut_for_the_snippet_but_kept_in_full():
    d = hit_to_dict(hit(texts={"ru": "Статья 1.\n" + "слово " * 300}), "en")
    assert d["snippet"].endswith("…") and len(d["snippet"]) <= 601 and len(d["texts"]["ru"]) > 1000


def test_filters_default_and_override():
    f = make_filters({})
    assert f.only_in_force and f.hide_drafts and f.kinds == ()
    g = make_filters({"only_in_force": False, "kinds": ["Кодекс"], "year_from": "2000"})
    assert not g.only_in_force and g.kinds == ("Кодекс",) and g.year_from == 2000
