from types import SimpleNamespace

import pytest

from summary_bot.errors import ErrorReporter, human_reason, message_link, retry


class Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kwargs):
        self.sent.append((chat_id, text, kwargs))


@pytest.mark.asyncio
async def test_retry_recovers_without_alert(monkeypatch):
    calls = 0

    async def no_sleep(_):
        pass

    async def operation():
        nonlocal calls
        calls += 1
        if calls < 3:
            raise TimeoutError()
        return "ok"

    monkeypatch.setattr("summary_bot.errors.asyncio.sleep", no_sleep)
    assert await retry(operation) == "ok"
    assert calls == 3


@pytest.mark.asyncio
async def test_media_alert_is_contextual_and_deduplicated():
    bot = Bot()
    reporter = ErrorReporter(bot, 7)
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-100123, title="Рабочая группа"),
        message_thread_id=42,
        message_id=99,
    )
    await reporter.media(message, "изображение", TimeoutError())
    await reporter.media(message, "изображение", TimeoutError())
    assert len(bot.sent) == 1
    text = bot.sent[0][1]
    assert "Рабочая группа" in text and "тема 42" in text
    assert "не ответил вовремя" in text
    assert "остальная переписка собирается" in text
    assert message_link(-100123, 99) in text
    assert human_reason(TimeoutError()) == "сервис не ответил вовремя"
