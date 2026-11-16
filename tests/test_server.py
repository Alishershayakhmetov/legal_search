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


def test_legal_force_prior_is_off_unless_requested():
    assert make_filters({}).force_prior == 0.0
    assert make_filters({"force_prior": 0.02}).force_prior == 0.02


def test_group_by_act_keeps_the_best_article_of_each_act_in_order():
    from engine import group_by_act
    hits = [hit(title="Трудовой кодекс", article_no="88"), hit(title="О правоохранительной службе", article_no="73"), hit(title="Трудовой кодекс", article_no="89"),
            hit(title="О государственной службе", article_no="40"), hit(title="Трудовой кодекс", article_no="90")]
    rows = group_by_act(hits, 3)
    assert [(h.title, h.article_no, n) for h, n in rows] == [("Трудовой кодекс", "88", 2), ("О правоохранительной службе", "73", 0), ("О государственной службе", "40", 0)]
