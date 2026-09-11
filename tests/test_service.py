from datetime import datetime
from zoneinfo import ZoneInfo

from summary_bot.service import is_due, period_label, period_start
from summary_bot.service import SummaryService

import pytest


TZ = ZoneInfo("Europe/Moscow")


def test_schedules():
    assert is_due("day", datetime(2026, 8, 20, 20, 0, tzinfo=TZ))
    assert is_due("week", datetime(2026, 8, 21, 20, 0, tzinfo=TZ))
    assert not is_due("week", datetime(2026, 8, 20, 20, 0, tzinfo=TZ))
    assert is_due("month", datetime(2026, 8, 31, 20, 0, tzinfo=TZ))
    assert not is_due("month", datetime(2026, 8, 30, 20, 0, tzinfo=TZ))


def test_period_windows():
    now = datetime(2026, 8, 31, 20, 0, tzinfo=TZ)
    assert period_start("day", now).date().isoformat() == "2026-08-30"
    assert period_start("week", now).date().isoformat() == "2026-08-24"
    assert period_start("month", now).date().isoformat() == "2026-08-01"
    assert period_label("day") == "24 часа"
    assert period_label("week") == "7 дней"
    assert period_label("month") == "30 дней"


@pytest.mark.asyncio
async def test_failed_thread_does_not_block_other_threads(monkeypatch):
    class Bot:
        def __init__(self): self.sent = []
        async def send_message(self, chat_id, text, **kwargs):
            self.sent.append((chat_id, text, kwargs))

    class DB:
        def __init__(self): self.finished = []
        async def get_group(self, _):
            return {"chat_id": -100123, "title": "Test", "status": "active", "period": "day"}
        async def message_threads(self, *_): return {1: ["bad"], 2: ["good"]}
        async def finish_thread(self, chat_id, thread_id, through):
            self.finished.append((chat_id, thread_id))

    class Summarizer:
        async def summarize(self, _, rows):
            if rows == ["bad"]: raise TimeoutError()
            return "готово"

    async def no_sleep(_): pass
    monkeypatch.setattr("summary_bot.errors.asyncio.sleep", no_sleep)
    bot, db = Bot(), DB()
    service = SummaryService(bot, db, Summarizer(), 7)
    assert await service.run_group(-100123) == 1
    assert db.finished == [(-100123, 2)]
    assert any(chat_id == 7 and "сообщения сохранены" in text for chat_id, text, _ in bot.sent)
    assert any("Сообщение от бота-суммаризатора" in text for _, text, _ in bot.sent)
    assert any("Автоматическая сводка переписки" in text for _, text, _ in bot.sent)


@pytest.mark.asyncio
async def test_excluded_thread_is_not_published():
    class Bot:
        def __init__(self): self.sent = []
        async def send_message(self, chat_id, text, **kwargs): self.sent.append(text)

    class DB:
        async def get_group(self, _):
            return {"chat_id": -100123, "title": "Test", "status": "active", "period": "week"}
        async def message_threads(self, *_): return {2449: ["note"]}
        async def finish_thread(self, *_): raise AssertionError("excluded topic must remain untouched")

    class Summarizer:
        async def summarize(self, *_): raise AssertionError("excluded topic must not be summarized")

    bot = Bot()
    service = SummaryService(bot, DB(), Summarizer(), 7, excluded_thread_ids={2449})
    assert await service.run_group(-100123) == 0
    assert bot.sent == []
