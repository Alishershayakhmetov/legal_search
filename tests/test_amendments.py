import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))

from amendments import parse_footnote, parse_notes, to_date  # noqa: E402

TODAY = date(2026, 11, 15)


def test_footnote_with_several_amendments_keeps_each_action_and_effective_date():
    line = ("Сноска. Закон дополнен статьей 43-8 в соответствии с Законом РК от 02.01.2021 № 402-VI (вводится в действие с 01.01.2022); "
            "с изменениями, внесенными законами РК от 09.04.2016 № 494-V (вводится в действие по истечении десяти календарных дней после дня его первого официального опубликования); "
            "от 19.04.2019 № 249-VI (порядок введения в действие см. ст. 2 ); исключена Законом РК от 28.12.2010 № 369-IV (вводится в действие с 01.01.2011).")
    e = parse_footnote(line)
    assert [x["number"] for x in e] == ["402-VI", "494-V", "249-VI", "369-IV"]
    assert [x["action"] for x in e] == ["дополнено", "изменено", "изменено", "исключено"]
    assert e[0]["effective_date"] == "2022-01-01" and "10 календарных" in e[1]["effective"] and "статьёй" in e[2]["effective"]


def test_kazakh_footnote_with_cyrillic_roman_numeral_and_old_date_format():
    e = parse_footnote("Ескерту. 82-бап жаңа редакцияда - ҚР 1998.03.02. № 211 Заңымен; өзгеріс енгізілді - ҚР 27.12.2019 № 292-VІ (қолданысқа енгізілу тәртібін 2-баптан қараңыз) Заңымен.", "kk")
    assert e[0]["date"] == "1998.03.02" and to_date(e[0]["date"]) == date(1998, 3, 2) and e[0]["action"] == "жаңа редакция"
    assert e[1]["number"] == "292-VІ" and e[1]["action"] == "өзгертілді"


def test_pending_note_gets_a_status_for_today_and_old_changes_are_dropped():
    text = ("1. Текст.\nПримечание ИЗПИ!\nВ пункт 4 предусмотрено изменение Законом РК от 03.01.2023 № 188-VII (вводится в действие с 01.01.2027).\n"
            "Примечание ИЗПИ!\nВ пункт 2 предусмотрено изменение Законом РК от 27.03.2023 № 216-VII (вводится в действие с 15.07.2024).\n"
            "Сноска. Статья 9 с изменением, внесенным Законом РК от 01.01.2020 № 1-VI (вводится в действие с 01.01.2021).")
    r = parse_notes(text, "ru", TODAY)
    assert [p["status"] for p in r["pending"]] == ["upcoming", "in_force_since_snapshot"]
    assert len(r["history"]) == 1 and r["history"][0]["effective_date"] == "2021-01-01"


def test_text_without_notes_has_no_history():
    assert parse_notes("Статья 1. Основные понятия\n1. Текст без сносок.", "ru", TODAY) == {"history": [], "pending": []}


def test_older_footnotes_with_spelled_out_dates():
    e = parse_footnote("Сноска. Статья 53 - в редакции Закона РК от 13 октября 2003 г. № 488; статья исключена - Законом РК от 10 июля 2003 года N 483 (вводится в действие с 1 января 2004 года).")
    assert [(x["date"], x["number"], x["action"]) for x in e] == [("13.10.2003", "488", "новая редакция"), ("10.07.2003", "483", "исключено")]
    assert e[1]["effective_date"] == "2004-01-01"


def test_kazakh_since_publication_is_not_read_as_a_number_of_days_and_duplicates_are_merged():
    e = parse_footnote("Ескерту. 14-бапқа өзгерістер енгізілді - ҚР 2012.07.10 № 34-V (алғашқы ресми жарияланған күнінен бастап қолданысқа енгізіледі); 17.11.2015 № 408-V (01.03.2016 бастап күшіне енеді).", "kk")
    assert e[0]["effective"] == "со дня первого официального опубликования" and e[1]["effective_date"] == "2016-03-01"
    text = "Сноска. Пункт 10 в редакции Закона РК от 13.06.2018 № 158-VI .\n1. Текст.\nСноска. Пункт 10 в редакции Закона РК от 13.06.2018 № 158-VI ."
    assert len(parse_notes(text, "ru", TODAY)["history"]) == 1


def test_consecutive_markers_do_not_produce_empty_notes():
    text = "Примечание ИЗПИ!\nПримечание ИЗПИ!\nВ пункт 4 предусмотрено изменение Законом РК от 27.03.2023 № 216-VII (вводится в действие с 15.07.2024).\nТекст."
    r = parse_notes(text, "ru", TODAY)
    assert len(r["pending"]) == 1 and r["pending"][0]["note"].startswith("В пункт 4")
