from types import SimpleNamespace

import pytest

from summary_bot.errors import EmptyProviderResponse, ErrorReporter, human_reason, message_link, retry


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
    await reporter.media(message, "изображение", "распознать изображение с помощью AI", TimeoutError())
    await reporter.media(message, "изображение", "распознать изображение с помощью AI", TimeoutError())
    assert len(bot.sent) == 1
    text = bot.sent[0][1]
    assert "Рабочая группа" in text and "тема 42" in text
    assert "изображение в сообщении №99" in text
    assert "распознать изображение с помощью AI" in text
    assert "не ответил вовремя" in text
    assert "остальная переписка собирается" in text
    assert message_link(-100123, 99) in text
    assert human_reason(TimeoutError()) == "сервис не ответил вовремя"


def test_provider_reason_includes_safe_status_and_detail():
    exc = RuntimeError("request failed")
    exc.status_code = 400
    exc.body = {"error": {"code": "InvalidParameter", "message": "Unsupported image format"}}
    assert human_reason(exc) == (
        "AI-сервис отклонил запрос (HTTP 400): "
        "InvalidParameter — Unsupported image format"
    )


def test_telegram_reason_names_telegram_not_ai():
    exc = RuntimeError("file is too big")
    exc.status_code = 400
    assert human_reason(exc, "Telegram").startswith("Telegram отклонил запрос (HTTP 400)")


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


def test_empty_response_reason_is_explicit():
    assert "ответил без текста" in human_reason(EmptyProviderResponse())


@pytest.mark.asyncio
async def test_media_alert_includes_filename():
    bot = Bot()
    reporter = ErrorReporter(bot, 7)
    message = SimpleNamespace(
        chat=SimpleNamespace(id=-100123, title="Рабочая группа"),
        message_thread_id=42,
        message_id=100,
        document=SimpleNamespace(file_name="схема.png"),
        audio=None,
    )
    await reporter.media(message, "изображение", "скачать файл изображения из Telegram", TimeoutError())
    assert "изображение «схема.png»" in bot.sent[0][1]
