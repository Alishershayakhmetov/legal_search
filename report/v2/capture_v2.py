"""Fresh screenshots of the running app for report/presentation v2 (reuses the DevTools helper of report/capture_screens.py without changing it)."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import capture_screens as c  # noqa: E402

c.OUT = Path(__file__).resolve().parent / "figures"
c.SHOTS = [
    ("app_search", "Какое наказание грозит за кражу?", "articles", "Язык запроса"),
    ("app_reference", "статья 188 УК", "articles", "Запрос содержит номер статьи"),
    ("app_regimes", "Сколько дней отпуска положено?", "regimes", "Одна лучшая статья"),
    ("app_offtopic", "Как приготовить плов в казане?", "articles", "Надёжной статьи"),
    ("app_english", "How long do I have to appeal a court decision?", "articles", "Язык запроса"),
]
asyncio.run(c.main())
