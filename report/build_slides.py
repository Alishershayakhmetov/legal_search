"""Build the defense presentation (pptx) from the result files. Native charts and tables, speaker notes included."""
import glob
import json
from pathlib import Path

from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LEGEND_POSITION, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "report" / "figures"
OUT = ROOT / "report" / "Презентация_Поиск_по_законодательству_РК.pptx"

NAVY, BLUE, GREY, LIGHT, ACCENT, GREEN = RGBColor(0x1F, 0x2A, 0x44), RGBColor(0x08, 0x51, 0x9C), RGBColor(0x59, 0x59, 0x59), RGBColor(0xEE, 0xF3, 0xFA), RGBColor(0xC0, 0x39, 0x2B), RGBColor(0x2E, 0x7D, 0x32)
FONT = "Calibri"


def load(pattern):
    rows = []
    for p in sorted(glob.glob(str(ROOT / "outputs" / pattern))):
        rows += json.loads(Path(p).read_text(encoding="utf-8"))
    return rows


SPARSE = load("sparse_results_articles_rukk_wordp5stem_v1.json")
SPARSE_ALL = load("sparse_results_all_*_v1.json")
DENSE = load("dense_results_*_articles_v1.json")
DENSE_ALL = load("dense_results_multilingual-e5-small_all_v1.json")
PAIRED = json.loads((ROOT / "outputs" / "paired_analysis.json").read_text(encoding="utf-8"))


def g(rows, **kw):
    return next(r for r in rows if all(r.get(k) == v for k, v in kw.items()))


def f2(x):
    return f"{x:.2f}".replace(".", ",")


prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def textbox(slide, x, y, w, h, text, size=18, bold=False, color=NAVY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    lines = text if isinstance(text, list) else [text]
    for i, line in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = align
        r = para.add_run()
        r.text = line
        r.font.size, r.font.bold, r.font.italic, r.font.name = Pt(size), bold, italic, FONT
        r.font.color.rgb = color
    return tb


def bullets(slide, x, y, w, h, items, size=18, gap=8):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    for i, it in enumerate(items):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.space_after = Pt(gap)
        bold_part, _, rest = it.partition("|")
        if rest:
            r1 = para.add_run(); r1.text = "• " + bold_part; r1.font.bold = True
            r2 = para.add_run(); r2.text = rest
            runs = (r1, r2)
        else:
            r1 = para.add_run(); r1.text = "• " + it
            runs = (r1,)
        for r in runs:
            r.font.size, r.font.name = Pt(size), FONT
            r.font.color.rgb = NAVY
    return tb


def new_slide(title, subtitle=None, notes=""):
    s = prs.slides.add_slide(BLANK)
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(0.12))
    bar.fill.solid(); bar.fill.fore_color.rgb = BLUE; bar.line.fill.background()
    textbox(s, 0.6, 0.35, 12.1, 0.8, title, size=30, bold=True)
    if subtitle:
        textbox(s, 0.6, 1.08, 12.1, 0.5, subtitle, size=16, color=GREY)
    s.notes_slide.notes_text_frame.text = notes
    n = len(prs.slides)
    textbox(s, 12.2, 7.05, 0.8, 0.3, str(n), size=11, color=GREY, align=PP_ALIGN.RIGHT)
    return s


def table(slide, x, y, w, rows, col_w, size=13, header=True, row_h=0.38):
    shape = slide.shapes.add_table(len(rows), len(rows[0]), Inches(x), Inches(y), Inches(w), Inches(row_h * len(rows)))
    tbl = shape.table
    for i, cw in enumerate(col_w):
        tbl.columns[i].width = Inches(cw)
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            cell.text = ""
            para = cell.text_frame.paragraphs[0]
            run = para.add_run()
            run.text = str(val)
            run.font.size, run.font.name = Pt(size), FONT
            run.font.bold = header and ri == 0
            run.font.color.rgb = RGBColor(255, 255, 255) if header and ri == 0 else NAVY
            cell.margin_left = cell.margin_right = Inches(0.06)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.fill.solid()
            cell.fill.fore_color.rgb = BLUE if header and ri == 0 else (LIGHT if ri % 2 == 0 else RGBColor(255, 255, 255))
        tbl.rows[ri].height = Inches(row_h)
    return tbl


def stat(slide, x, y, w, number, caption, color=BLUE):
    box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(1.45))
    box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
    textbox(slide, x, y + 0.1, w, 0.7, number, size=34, bold=True, color=color, align=PP_ALIGN.CENTER)
    textbox(slide, x + 0.1, y + 0.85, w - 0.2, 0.55, caption.split(chr(10)), size=13, color=GREY, align=PP_ALIGN.CENTER)


b_ru, b_kk, b_en = (g(DENSE, model="bge-m3", lang="ru", system="dense"), g(DENSE, model="bge-m3", lang="kk", system="dense"), g(DENSE, model="bge-m3", lang="en", system="dense_cross"))
bm_ru, bm_kk = g(SPARSE, lang="ru", analyzer="stem", scheme="bm25"), g(SPARSE, lang="kk", analyzer="p5", scheme="bm25")

# 1 -------------------------------------------------------------------- title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
textbox(s, 0.9, 1.3, 11.5, 2.3, ["Многоязычный поиск по законодательству", "Республики Казахстан"], size=40, bold=True, color=RGBColor(255, 255, 255))
textbox(s, 0.9, 3.9, 11.5, 0.8, "От названий актов к статьям: вопрос на казахском, русском или английском", size=22, color=RGBColor(0xBF, 0xD4, 0xEE))
textbox(s, 0.9, 5.4, 11.5, 1.2, ["Итоговый проект · Programming for Data Analysis and Database · Тема 16", "[ФИО, группа]  ·  [преподаватель]  ·  Астана, 2026"], size=16, color=RGBColor(0xBF, 0xD4, 0xEE))
s.notes_slide.notes_text_frame.text = ("Здравствуйте. Тема 16 — поисковик по законодательству Казахстана. В исходной постановке он ищет акт по казахскому названию. "
                                       "Я расширил её: вопрос можно задать на трёх языках, а искать — по текстам статей. Расскажу, как это сделано, как проверено и что получилось. Около 10 минут.")

# 2 -------------------------------------------------------------------- problem
s = new_slide("Задача: найти статью, которая отвечает на вопрос",
              "Не «найти акт по названию», а «работодатель второй месяц не платит зарплату — что делать?»",
              "Задача из темы 16 — найти акт по названию. Но человек приходит с ситуацией. Ему нужна статья, например ст. 113 Трудового кодекса о сроках выплаты зарплаты. "
              "Три трудности: бытовые слова не совпадают с юридическими; казахский язык агглютинативен — одно понятие встречается в десятках форм; "
              "в базе нет английских текстов, а запросы могут быть на английском.")
bullets(s, 0.6, 1.9, 6.3, 4.5, [
    "Как в теме 16|: акты ищутся по названию, метаданные без текстов.",
    "Что добавлено|: три языка запроса (kk · ru · en), поиск по текстам статей, оценка на размеченных вопросах.",
    "Чем трудно|: бытовая лексика ≠ юридическая; агглютинативный казахский; нет английских текстов; много проектов и редакций с одинаковым текстом.",
], size=19, gap=14)
box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.3), Inches(1.9), Inches(5.4), Inches(4.2))
box.fill.solid(); box.fill.fore_color.rgb = LIGHT; box.line.fill.background()
textbox(s, 7.55, 2.05, 4.9, 0.4, "Пример", size=14, bold=True, color=GREY)
textbox(s, 7.55, 2.5, 4.9, 1.0, "«Начальник уже второй месяц не платит зарплату. Что делать?»", size=19, italic=True)
textbox(s, 7.55, 3.7, 4.9, 0.4, "Нужное:", size=14, bold=True, color=GREY)
textbox(s, 7.55, 4.1, 4.9, 1.6, ["Трудовой кодекс, ст. 113 «Порядок и сроки выплаты заработной платы»", "КоАП, ст. 87 «Нарушение требований по оплате труда»"], size=16)

# 3 -------------------------------------------------------------------- data
s = new_slide("Данные: три источника, 7,1 ГБ текста", "Метаданные + полные тексты + ссылка на официальный сайт",
              "KazakhLawCorpus — это метаданные 223 тысяч актов: названия на казахском и русском, вид, орган, даты, статус. Текстов в нём нет. "
              "Тексты я взял из набора Mendeley Textual Foundations of Justice — 204 тысячи файлов с действующим законодательством на двух языках, лицензия CC BY 4.0. "
              "Официальный сайт adilet.zan.kz рисует страницы скриптами, API закрыт в robots.txt, поэтому я его не скачивал — только даю ссылки. "
              "Обещанных в описании файлов с историей и цитированием в репозитории нет, поэтому графа цитирования нет.")
stat(s, 0.6, 1.9, 2.9, "223 245", "акта в метаданных\n(CSV 952 МБ → Parquet 30 МБ)")
stat(s, 3.7, 1.9, 2.9, "204 тыс.", "текстовых файлов\nru 102 596 · kk 101 304")
stat(s, 6.8, 1.9, 2.9, "3,08 млн", "фрагментов после\nнарезки текстов")
stat(s, 9.9, 1.9, 2.9, "1,0 ГБ", "база SQLite,\n13 таблиц")
bullets(s, 0.6, 3.7, 12.1, 3.2, [
    "Аудит метаданных|: 3,3% казахских названий пусты, ~60 заменены текстом капчи; дата публикации пуста у 89% актов; у 6 актов нет даты принятия.",
    "Тексты|: только действующее право: тексты есть у 59,9% действующих актов и лишь у 4,5% утративших силу (SQL-запрос 4).",
    "Лицензии и этика|: CC BY 4.0 и Apache 2.0; массовое скачивание adilet не выполнялось.",
], size=17, gap=10)

# 4 -------------------------------------------------------------------- pipeline
s = new_slide("Конвейер: от CSV до поиска", "Каждый шаг — отдельный скрипт, порядок запуска зафиксирован",
              "Конвейер: CSV читается блоками и сохраняется в Parquet, дальше загрузка в SQLite с нормализацией. Затем тексты связываются с актами, режутся на фрагменты, "
              "и по ним строятся индексы: BM25 и эмбеддинги. Сверху — приложение. Самое трудоёмкое и рискованное — связка файлов с актами, о ней следующий слайд.")
s.shapes.add_picture(str(FIG / "fig_pipeline.png"), Inches(0.6), Inches(1.9), width=Inches(12.1))
bullets(s, 0.6, 5.0, 12.1, 2.0, [
    "Загрузка|: чанки по 100 тыс. строк, 22 нужные колонки из 49, Parquet со сжатием: 952 МБ → 30 МБ за 5 секунд.",
    "Нарезка|: статьи — одним фрагментом, остальное — по абзацам до 1 500 символов; 15 процессов, около 2 минут на язык.",
], size=17, gap=8)

# 5 -------------------------------------------------------------------- linking
s = new_slide("Самое трудное: связать файл с актом", "В именах файлов нет идентификатора акта, а названия обрезаны до 200 символов",
              "Файл называется «название + метка статуса + вид акта + орган + дата», обрезанное до 200 символов. Связываю по началу имени, потом по дате из хвоста, по номеру акта и по органу. "
              "Проверка: у однозначных совпадений дата из имени равна дате принятия в 96,8% и 98,7%. Важно: первая версия потеряла главные кодексы — названия короче пяти слов не находились. "
              "Ошибку нашёл, когда составлял тестовые запросы и не нашёл Трудовой кодекс. После исправления без совпадения осталось 120 файлов вместо 2 392. "
              "Это урок: общий процент связки скрывал, что хуже всего связаны самые важные акты. "
              "Оставшиеся 20% файлов — длинные названия, обрезанные до даты; они остаются в поиске, но без точной ссылки.")
table(s, 0.6, 1.9, 6.6, [["", "Русский", "Казахский"], ["Привязано к акту", "79,8%", "81,1%"], ["Различных актов с текстом", "80 916", "78 250"],
                          ["Дата из имени = дата акта", "96,8%", "98,7%"], ["Не определено", "20,2%", "18,9%"]], [3.4, 1.6, 1.6], size=15, row_h=0.5)
textbox(s, 0.6, 4.6, 6.6, 0.4, "Метод: название → дата → номер → орган/регион", size=15, color=GREY)
box = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.6), Inches(1.9), Inches(5.1), Inches(4.4))
box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xFD, 0xED, 0xEC); box.line.fill.background()
textbox(s, 7.85, 2.05, 4.6, 0.4, "Найденная ошибка", size=14, bold=True, color=ACCENT)
textbox(s, 7.85, 2.55, 4.6, 3.6, ["Названия короче 5 слов не находились:", "«Трудовой кодекс», КоАП, Уголовный и Земельный кодексы оставались без текстов.",
                                  "", "Было без совпадения: 2 392 файла", "Стало: 120", "", "Урок: общий процент скрывал худшее для самых важных актов."], size=16)

# 6 -------------------------------------------------------------------- SQL
s = new_slide("База данных: 13 таблиц, 13 запросов", "Нормализация, связи «многие-ко-многим», оконные функции",
              "Схема в третьей нормальной форме. Многозначные поля — формы акта, сферы регулирования, органы — вынесены в таблицы связей. "
              "В таблице passage нет law_id и языка — они определяются через file_id. 13 запросов: CTE, JOIN, HAVING, подзапросы, LAG, RANK, ROW_NUMBER, накопительные суммы. "
              "Результаты используются в анализе: например, запрос 4 показал, что тексты есть почти только у действующих актов, а запрос 7 — что 40% актов делят название с другими, "
              "и значит, поиск по названию неоднозначен.")
s.shapes.add_picture(str(ROOT / "docs" / "er_diagram.png"), Inches(0.5), Inches(1.7), height=Inches(5.2))
bullets(s, 8.6, 1.9, 4.3, 5.0, [
    "13 запросов|: CTE, JOIN, HAVING, подзапросы, LAG, RANK, ROW_NUMBER, SUM OVER.",
    "Запрос 4|: тексты есть у 59,9% действующих и 4,5% утративших силу актов.",
    "Запрос 7|: 40% актов делят название с другими.",
    "Запрос 13|: 8% фрагментов — статьи, 52% — прочий текст, 40% — таблицы.",
], size=16, gap=10)

# 7 -------------------------------------------------------------------- test set
s = new_slide("Как измерять: тестовый набор вопросов", "53 потребности × 3 языка = 159 запросов, 376 оценённых статей",
              "Чтобы считать Recall и MRR, нужен эталон: какие статьи верны. Я составил 53 бытовые потребности. На каждую — запрос на трёх языках. "
              "Первый раунд оценок — статьи подобраны вручную, у 54 из 102 я прочитал текст. Второй раунд — метод пулинга: взял топ-10 восьми прогонов систем, "
              "270 новых статей прочитал и оценил. Итого 376 статей: 67 прямо отвечают, 100 связаны, 209 прочитаны и отвергнуты. "
              "Версии одного акта — проект, компиляция — объединяю сравнением хеша текста. Честная оговорка: оценки мои вместе с ИИ-ассистентом и пока не проверены независимо; "
              "казахские формулировки нужно проверить носителю. Поэтому цифры предварительные.")
table(s, 0.6, 1.9, 7.4, [["Вид потребности", "Число", "Пример"], ["Ситуация", "30", "Меня заставляют работать сверхурочно"],
                          ["Прямой вопрос", "15", "Какая ставка НДС в Казахстане?"], ["Название акта", "8", "закон о защите прав потребителей"]], [2.3, 0.9, 4.2], size=14, row_h=0.55)
bullets(s, 8.3, 1.9, 4.5, 4.6, [
    "Оценка|: «акт + статья»; версии и проекты объединены по хешу текста.",
    "Метрики|: Success@k, Recall@50, MRR@10, nDCG@10, бутстрэп 95%.",
    "Раунд 2|: пул из 8 прогонов систем: +270 статей.",
], size=16, gap=10)
table(s, 0.6, 4.4, 7.4, [["Версия", "Оценённых статей", "Отвечают", "Связаны", "Не подходят"], ["v0", "102", "58", "44", "—"], ["v1", "376", "67", "100", "209"]], [1.3, 2.2, 1.4, 1.3, 1.2], size=14, row_h=0.5)
textbox(s, 0.6, 6.2, 12.1, 0.7, "Оценки составлены автором с ИИ-ассистентом и пока не проверены независимо.", size=15, color=ACCENT, bold=True)

# 8 -------------------------------------------------------------------- methods
s = new_slide("Что сравнивали", "Базовый метод → слова (BM25) → смысл (эмбеддинги) → гибрид",
              "Базовый метод — число совпавших слов. TF-IDF и BM25 по трём вариантам обработки слов: словоформы, первые пять букв и стемминг (Snowball для русского, "
              "своё отсечение суффиксов для казахского). Плотный поиск — три мультиязычные модели; все без дообучения, то есть утечки между обучением и тестом нет. "
              "Гибрид — слияние рангов RRF. Для английского: прямой поиск моделью против перевода запроса NLLB на русский и казахский.")
table(s, 0.6, 1.9, 12.1, [["Подход", "Что это", "Параметры"],
                           ["Базовый", "число совпавших слов запроса", "—"],
                           ["TF-IDF · BM25", "поиск по словам; 3 варианта обработки: словоформы / 5 букв / стемминг", "k1 = 1,2; b = 0,75"],
                           ["e5-small · e5-base · bge-m3", "смысловой поиск, мультиязычные эмбеддинги, без дообучения", "118 / 278 / 568 млн"],
                           ["Гибрид", "слияние BM25 и смыслового поиска (RRF)", "равные веса"],
                           ["Английский", "напрямую против перевода запроса (NLLB-600M)", "—"]], [3.4, 6.5, 2.2], size=15, row_h=0.62)
textbox(s, 0.6, 6.0, 12.1, 0.8, "Модели без обучения → разбиения на обучение и тест нет, утечки нет; оценка на независимо составленных вопросах.", size=16, color=GREY, italic=True)

# 9 -------------------------------------------------------------------- results
s = new_slide("Главный результат: смысловой поиск bge-m3", "Доля вопросов, у которых нужная статья среди первых 10 результатов",
              f"Главный график. Для русских вопросов BM25 находит нужную статью в первой десятке в {f2(bm_ru['success@10'])} случаев, bge-m3 — в {f2(b_ru['success@10'])}. "
              f"Для казахских {f2(bm_kk['success@10'])} против {f2(b_kk['success@10'])}. Английский BM25 не поддерживает, а bge-m3 находит в {f2(b_en['success@10'])} случаев прямо, без перевода. "
              "Интервалы MRR у bge-m3 и BM25 не пересекаются, то есть разница не шум. При этом e5-base на казахском хуже e5-small — различия внутри интервалов. "
              "Попарно: на русском bge-m3 находит 19 потребностей, которых BM25 не находит, а BM25 — только 2, которых не находит bge-m3.")
cd = CategoryChartData()
cd.categories = ["русский", "казахский", "английский"]
series = [("BM25", [bm_ru["success@10"], bm_kk["success@10"], None]),
          ("e5-small", [g(DENSE, model="multilingual-e5-small", lang=l, system="dense" if l != "en" else "dense_cross")["success@10"] for l in ("ru", "kk", "en")]),
          ("e5-base", [g(DENSE, model="multilingual-e5-base", lang=l, system="dense" if l != "en" else "dense_cross")["success@10"] for l in ("ru", "kk", "en")]),
          ("bge-m3", [b_ru["success@10"], b_kk["success@10"], b_en["success@10"]])]
for name, vals in series:
    cd.add_series(name, vals)
gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(0.6), Inches(1.7), Inches(8.2), Inches(5.2), cd)
ch = gf.chart
ch.has_legend, ch.legend.position, ch.legend.include_in_layout = True, XL_LEGEND_POSITION.BOTTOM, False
ch.legend.font.size = Pt(14)
for ser, col in zip(ch.plots[0].series, ("8C8C8C", "9ECAE1", "4292C6", "08519C")):
    ser.format.fill.solid(); ser.format.fill.fore_color.rgb = RGBColor.from_string(col)
pl = ch.plots[0]
pl.has_data_labels = True
pl.data_labels.number_format, pl.data_labels.number_format_is_linked = "0.00", False
pl.data_labels.font.size, pl.data_labels.position = Pt(12), XL_LABEL_POSITION.OUTSIDE_END
ch.value_axis.maximum_scale, ch.value_axis.minimum_scale = 1.0, 0
ch.value_axis.tick_labels.font.size = Pt(12)
ch.category_axis.tick_labels.font.size = Pt(14)
ch.value_axis.has_major_gridlines = False
bullets(s, 9.1, 1.9, 3.8, 4.8, [
    "bge-m3|: " + f"{f2(b_ru['success@10'])} (ru), {f2(b_kk['success@10'])} (kk), {f2(b_en['success@10'])} (en, без перевода)",
    "BM25|: " + f"{f2(bm_ru['success@10'])} (ru), {f2(bm_kk['success@10'])} (kk), английский не поддерживает",
    "Попарно, ru|: bge-m3 находит 19 потребностей, которых BM25 не находит; BM25 — 2",
    "Интервалы MRR не пересекаются",
], size=15, gap=10)

# 10 ------------------------------------------------------------------- analyzers + scope
s = new_slide("Что ещё выяснилось", "Стемминг, объём корпуса и английские запросы",
              "Первое: для русского стемминг заметно лучше словоформ — 0,42 против 0,24. Для казахского Success@10 одинаков у трёх вариантов, а по MRR лучше простые первые пять букв: "
              "самодельный стеммер выигрыша не дал. Второе: если искать не только по статьям, а по всему тексту — 1,7 миллиона фрагментов — все системы теряют качество, но порядок сохраняется. "
              "Третье: для английского bge-m3 перевод не нужен; для e5 прямой поиск слаб, и перевод помогает.")
s.shapes.add_picture(str(FIG / "fig_scope.png"), Inches(0.6), Inches(1.7), width=Inches(5.6))
s.shapes.add_picture(str(FIG / "fig_english.png"), Inches(7.0), Inches(1.7), width=Inches(5.6))
textbox(s, 0.6, 4.72, 6.1, 0.4, "Объём корпуса: только статьи или весь текст", size=14, color=GREY, bold=True)
textbox(s, 7.0, 4.72, 6.1, 0.4, "Английские запросы: напрямую или через перевод", size=14, color=GREY, bold=True)
bullets(s, 0.6, 5.3, 12.2, 1.7, [
    "Обработка слов|: русский — стемминг (0,42 против 0,24 у словоформ); казахский — пять букв, самодельный стеммер выигрыша не дал.",
    "Больше корпус — хуже поиск|: на 1,7 млн фрагментов все системы теряют качество, порядок сохраняется.",
    "Гибрид с равными весами|: хуже одного bge-m3, потому что BM25 заметно слабее.",
], size=15, gap=5)

# 11 ------------------------------------------------------------------- cost
s = new_slide("Цена качества: время и память", "RTX 3050 Laptop 4 ГБ, 16 ГБ ОЗУ, fp16, 384 токена",
              "Выбор модели — это компромисс. bge-m3 кодирует 53 фрагмента в секунду, поэтому статьи индексируются час, а весь корпус — девять часов. "
              "e5-small в шесть раз быстрее. Для приложения я выбрал bge-m3: на казахском он вдвое точнее e5-base, а задержка запроса остаётся около сорока миллисекунд. "
              "Весь корпус кодировал только e5-small — около полутора часов.")
rows = [["Метод", "Индекс статей, мин", "Размер индекса", "Мс на запрос", "Success@10 ru / kk"]]
rows.append(["BM25", "десятки секунд", "92 МБ", f"{g(SPARSE, lang='ru', analyzer='stem', scheme='bm25')['ms_per_query']:.0f}", f"{f2(bm_ru['success@10'])} / {f2(bm_kk['success@10'])}"])
for model, name, mins, dim in (("multilingual-e5-small", "e5-small", "8,9", 384), ("multilingual-e5-base", "e5-base", "27,0", 768), ("bge-m3", "bge-m3", "62,3", 1024)):
    r, k = g(DENSE, model=model, lang="ru", system="dense"), g(DENSE, model=model, lang="kk", system="dense")
    rows.append([name, mins, f"{230545 * dim * 2 // 1_000_000} МБ", f"{r['ms_per_query']:.0f}", f"{f2(r['success@10'])} / {f2(k['success@10'])}"])
table(s, 0.6, 1.9, 12.1, rows, [2.4, 2.6, 2.4, 2.1, 2.6], size=16, row_h=0.62)
bullets(s, 0.6, 5.3, 12.1, 1.6, [
    "Скорость кодирования|: e5-small 377, e5-base 161, bge-m3 53 фрагмента/с.",
    "Весь корпус (1,7 млн) bge-m3|: около 9 часов, не выполнено; e5-small на всём тексте: около 1,3 часа, 1,3 ГБ.",
], size=16, gap=6)

# 12 ------------------------------------------------------------------- errors
s = new_slide("Где система ошибается", "bge-m3 не находит эталон в топ-10 для 9 из 45 русских запросов",
              "Разбор девяти промахов показал четыре типа. Первый — близкие, но не эталонные статьи: это чаще неполный эталон, а не ошибка поиска. "
              "Второй — другая редакция или проект кодекса. Третий — общее и особое регулирование: на вопрос об отпуске выше стоит закон о правоохранительной службе. "
              "Четвёртый — похожие нормы других законов: банкротство организаций вместо банкротства граждан. Каждый тип подсказывает улучшение — это следующий этап.")
table(s, 0.6, 1.9, 12.1, [["Тип ошибки", "Пример", "Что с этим делать"],
                           ["Близкая, но не эталонная статья", "Усыновление: выданы ст. 93, 95, 96 о согласии вместо ст. 91", "Расширить оценки"],
                           ["Другая редакция или проект", "КоАП: статьи о курении из прежней редакции кодекса", "Понижать проекты и старые редакции"],
                           ["Общий и особый режим", "Отпуск: закон о правоохранительной службе (30 дней) выше Трудового кодекса (24 дня)", "Учитывать категорию лица"],
                           ["Норма другого закона", "Банкротство гражданина: нормы о банкротстве организаций", "Повторное ранжирование топ-k"]], [3.2, 6.0, 2.9], size=14, row_h=0.8)

# 13 ------------------------------------------------------------------- demo
s = new_slide("Демонстрация: приложение", "Веб-страница · вопрос на kk / ru / en · ссылка на акт · фильтры · сравнение методов",
              "Показываю вживую. Ввожу вопрос — язык определяется по алфавиту, поиск идёт по 230 тысячам фрагментов статей, ответ за одну-четыре секунды. В карточке название акта, статья, "
              "статус, текст на языке вопроса, полный текст на русском и казахском во вкладках и ссылка на adilet.zan.kz. Фильтры: только действующие, скрыть проекты, вид акта, год. "
              "Режим сравнения показывает три метода рядом — для английского BM25 честно сообщает, что не применим. Кнопки «палец вверх/вниз» сохраняют оценки в файл. "
              "Запасной вариант на случай сбоя — эти скриншоты. Что не проверено: фильтры кроме настроек по умолчанию и работа без GPU.")
for x, name, cap in ((0.6, "app_search", "Поиск по статьям"), (4.75, "app_article_ref", "«статья 1 конституции рк»"), (8.9, "app_compare", "Сравнение методов")):
    s.shapes.add_picture(str(FIG / f"{name}.png"), Inches(x), Inches(1.65), width=Inches(3.95))
    textbox(s, x, 4.25, 3.95, 0.35, cap, size=12, color=GREY, align=PP_ALIGN.CENTER)
bullets(s, 0.6, 4.75, 12.2, 2.3, [
    "Режимы|: поиск по статьям (bge-m3 / BM25 / гибрид), поиск акта по названию, сравнение методов.",
    "Фильтры и примеры|: настройки в панели справа; все 53 вопроса тестового набора на каждом языке — готовые примеры.",
    "Ссылка на статью|: «статья 1 Конституции РК», «ст. 188 УК» — статья находится по номеру и показывается первой.",
    "Скорость|: 1–4 секунды на запрос на GPU; 👍/👎 пишутся в файл как новые оценки.",
], size=15, gap=5)

# 14 ------------------------------------------------------------------- limits and conclusions
s = new_slide("Выводы и ограничения", None,
              "Выводы: смысловой мультиязычный поиск заметно лучше поиска по словам для вопросов в свободной форме; bge-m3 работает кросс-языково, и перевод запроса не нужен; "
              "состав индекса важен не меньше модели; связку данных нужно проверять отдельно. Ограничения важны для честности: оценки мои и не проверены независимо, набор мал, "
              "поэтому различия в несколько пунктов недоказательны; лучшая модель проверена только на индексе статей; нет графа цитирования. "
              "Дальше: независимая проверка оценок, индексация всего корпуса bge-m3, понижение проектов и старых редакций, повторное ранжирование.")
textbox(s, 0.6, 1.3, 6.0, 0.5, "Выводы", size=22, bold=True, color=GREEN)
bullets(s, 0.6, 1.9, 6.0, 5.0, [
    f"Смысл бьёт слова|: bge-m3 {f2(b_ru['success@10'])} (ru), {f2(b_kk['success@10'])} (kk) против BM25 {f2(bm_ru['success@10'])} и {f2(bm_kk['success@10'])}.",
    f"Английский без перевода|: {f2(b_en['success@10'])} — модель кросс-языковая.",
    "Индекс важен как модель|: поиск по статьям лучше, чем по всему тексту.",
    "Данные нужно проверять|: ошибка связки теряла главные кодексы.",
], size=16, gap=10)
textbox(s, 6.9, 1.3, 6.0, 0.5, "Ограничения", size=22, bold=True, color=ACCENT)
bullets(s, 6.9, 1.9, 6.0, 5.0, [
    "Оценки мои и не проверены независимо|; набор неполон, метрики занижены.",
    "45 вопросов на язык|: интервалы ±0,1, малые различия — шум.",
    "bge-m3 не проверен на всём корпусе|: ~9 часов индексации.",
    "Нет графа цитирования|, нет перевода названий, нет дообучения.",
    "Справка, а не юридическая консультация|; тексты на 01.04.2024.",
], size=16, gap=10)

# 15 ------------------------------------------------------------------- next + thanks
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
textbox(s, 0.9, 1.4, 11.5, 1.0, "Что дальше", size=36, bold=True, color=RGBColor(255, 255, 255))
bullets_tb = bullets(s, 0.9, 2.5, 11.5, 3.2, [
    "Независимая проверка оценок и казахских запросов носителем языка",
    "Индексация всего корпуса bge-m3 и сравнение по всему тексту",
    "Понижать проекты и старые редакции; учитывать общий и специальный режим",
    "Повторное ранжирование топ-k и перевод названий актов на английский",
], size=22, gap=14)
for para in bullets_tb.text_frame.paragraphs:
    for r in para.runs:
        r.font.color.rgb = RGBColor(0xBF, 0xD4, 0xEE)
textbox(s, 0.9, 5.9, 11.5, 0.8, "Спасибо! Вопросы?", size=32, bold=True, color=RGBColor(255, 255, 255))
s.notes_slide.notes_text_frame.text = ("Возможные вопросы. 1) Почему не дообучали модель? — Нет обучающей выборки запрос–статья; разметка только для оценки. "
                                       "2) Почему гибрид хуже? — BM25 заметно слабее; веса не подбирал, чтобы не подгонять под 45 запросов. 3) Насколько можно верить цифрам? — "
                                       "Оценки мои и не проверены независимо, поэтому предварительные; порядок систем устойчив к расширению разметки. 4) Почему не весь корпус на bge-m3? — около 9 часов на ноутбуке. "
                                       "5) Как избегали утечки? — модели без обучения, разбиения нет; дубликаты версий объединены по хешу текста. 6) Что за ошибка в связке? — короткие названия, слайд 5.")

prs.save(OUT)
print("saved", OUT, "| slides", len(prs.slides))
