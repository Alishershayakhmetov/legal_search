import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from chunking import MAX_CHARS, OVERLAP, chunk_text, clean, pack  # noqa: E402

RU_CODE = """Раздел 1. Общие положения

Глава 1. Основные положения

Статья 1. Основные понятия
1. В настоящем Кодексе используются следующие понятия: работодатель, работник, трудовой договор.

Статья 2. Задачи Кодекса
1. Задачами настоящего Кодекса являются защита прав работников и работодателей.

Глава 2. Трудовой договор

Статья 3. Заключение договора
1. Трудовой договор заключается в письменной форме между работником и работодателем.
"""

KK_CODE = (
    "1-бап. Негізгі ұғымдар 1. Осы Кодексте мынадай ұғымдар пайдаланылады: жұмыс беруші, қызметкер, еңбек шарты.\n\n"
    "2-бап. Кодекстің міндеттері 1. Осы Кодекстің міндеті қызметкерлер мен жұмыс берушілердің құқықтарын қорғау.\n\n"
    "3-бап. Шарт жасасу 1. Еңбек шарты қызметкер мен жұмыс беруші арасында жазбаша түрде жасалады.\n"
)


def test_clean_normalises_whitespace():
    assert clean("a \xa0 b\r\n\n\n\nc ") == "a b\n\nc"


def test_article_mode_ru_one_passage_per_article_with_section():
    passages, stats = chunk_text(RU_CODE, "ru")
    assert stats["article_mode"] == 1
    assert [p["article_no"] for p in passages] == ["1", "2", "3"]
    assert passages[0]["heading"] == "Основные понятия"
    assert passages[0]["section"].startswith("Глава 1")
    assert passages[2]["section"].startswith("Глава 2")


def test_article_mode_kk_heading_stops_before_first_point():
    passages, _ = chunk_text(KK_CODE, "kk")
    assert [p["article_no"] for p in passages] == ["1", "2", "3"]
    assert passages[0]["heading"] == "Негізгі ұғымдар"


def test_plain_act_without_articles_is_not_article_mode():
    passages, stats = chunk_text("Правительство Республики Казахстан ПОСТАНОВЛЯЕТ:\n1. Утвердить прилагаемые правила работы.", "ru")
    assert stats["article_mode"] == 0
    assert len(passages) == 1 and passages[0]["article_no"] is None


def test_long_text_is_split_within_limits_and_loses_nothing():
    sentence = "Работодатель обязан выплатить работнику заработную плату в установленный срок. "
    text = "1. " + sentence * 200
    chunks = pack(clean(text))
    assert len(chunks) > 1
    assert all(len(c) <= MAX_CHARS + OVERLAP for c in chunks)
    joined = " ".join(chunks)
    assert joined.count("заработную плату") >= 200


def test_numeric_tables_are_dropped():
    passages, stats = chunk_text("1 2 3 4 5 6 7 8 9\n10 20 30 40 50\n" * 40, "ru")
    assert passages == [] and stats["dropped"] >= 1


def test_table_passages_are_flagged_not_dropped():
    rows = "\n".join(f"| 0{i} | Индивидуальный подоходный налог с доходов | 1 {i}" for i in range(10))
    passages, _ = chunk_text(rows, "ru")
    assert passages and all(p["is_table"] for p in passages)
    prose, _ = chunk_text("Работодатель обязан выплатить заработную плату работнику в срок.", "ru")
    assert not prose[0]["is_table"]


def test_start_char_points_into_cleaned_text():
    text = "Первый абзац про налоги и сборы в республике.\n\n" + "Второй абзац " * 150
    passages, _ = chunk_text(text, "ru")
    cleaned = clean(text)
    assert all(cleaned[p["start_char"]: p["start_char"] + 20] == p["text"][:20] for p in passages)


def test_headings_without_a_period_are_articles():
    ru = "Раздел I. Общие положения\nСтатья 1\n1. Республика Казахстан утверждает себя демократическим государством.\n\nСтатья 2\n1. Республика является унитарным государством.\n\nСтатья 3\n1. Государственная власть в Республике едина.\n"
    passages, stats = chunk_text(ru, "ru")
    assert stats["article_mode"] == 1
    assert [p["article_no"] for p in passages] == ["1", "2", "3"]
    kk = "1-бап\n1. Қазақстан Республикасы өзін демократиялық мемлекет ретінде орнықтырады.\n\n2-бап\n1. Республика біртұтас мемлекет болып табылады.\n\n3-бап\n1. Мемлекеттік билік Республикада біртұтас.\n"
    passages, _ = chunk_text(kk, "kk")
    assert [p["article_no"] for p in passages] == ["1", "2", "3"]


def test_a_sentence_starting_with_article_is_not_a_heading():
    text = "Статья 5 настоящего Закона предусматривает порядок выплаты заработной платы работникам в установленный срок.\nСтатья 6 настоящего Закона предусматривает ответственность работодателя за нарушение этого порядка выплаты.\n"
    _, stats = chunk_text(text, "ru")
    assert stats["article_mode"] == 0
