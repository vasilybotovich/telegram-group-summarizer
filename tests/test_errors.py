import pytest

from summary_bot.errors import ErrorReporter, human_reason, retry


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


def test_provider_reason_includes_safe_status_and_detail():
    exc = RuntimeError("request failed")
    exc.status_code = 400
    exc.body = {"error": {"code": "InvalidParameter", "message": "Unsupported input"}}
    assert human_reason(exc) == (
        "AI-сервис отклонил запрос (HTTP 400): "
        "InvalidParameter — Unsupported input"
    )


def test_connection_read_failure_is_specific():
    class ReadError(Exception):
        pass

    try:
        try:
            raise ReadError()
        except ReadError as cause:
            raise RuntimeError("Connection error") from cause
    except RuntimeError as exc:
        assert human_reason(exc) == "соединение с AI-сервис оборвалось при чтении ответа"


@pytest.mark.asyncio
async def test_summary_alert_is_contextual_and_deduplicated():
    bot = Bot()
    reporter = ErrorReporter(bot, 7)
    group = {"chat_id": -100123, "title": "Рабочая группа"}
    await reporter.summary(group, 42, TimeoutError())
    await reporter.summary(group, 42, TimeoutError())
    assert len(bot.sent) == 1
    text = bot.sent[0][1]
    assert "Рабочая группа" in text and "тема 42" in text
    assert "сообщения сохранены" in text
