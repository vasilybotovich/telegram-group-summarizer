from __future__ import annotations

import asyncio
import html
import re
import time
from collections.abc import Awaitable, Callable


async def retry(operation: Callable[[], Awaitable], attempts: int = 3):
    last_error = None
    for attempt in range(attempts):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt + 1 < attempts:
                await asyncio.sleep(0.5 * (2 ** attempt))
    raise last_error


class EmptyProviderResponse(RuntimeError):
    """The provider request succeeded but returned no usable text."""


def _safe_provider_detail(exc: Exception) -> str:
    body = getattr(exc, "body", None)
    if isinstance(body, dict):
        error = body.get("error", body)
        if isinstance(error, dict):
            code = error.get("code")
            message = error.get("message")
            detail = " — ".join(str(value) for value in (code, message) if value)
        else:
            detail = str(error)
    else:
        detail = str(exc)
    detail = re.sub(r"(?i)(bearer\s+|api[_-]?key[=:\s]+)\S+", r"\1***", detail)
    detail = re.sub(r"https?://[^\s/@]+:[^\s/@]+@", "https://***:***@", detail)
    return " ".join(detail.split())[:240]


def human_reason(exc: Exception, service: str = "AI-сервис") -> str:
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    chain_names = {type(error).__name__.lower() for error in _exception_chain(exc)}
    detail = _safe_provider_detail(exc)
    if isinstance(exc, EmptyProviderResponse):
        return f"{service} ответил без текста, поэтому результат нельзя добавить в сводку"
    if status == 429 or "rate limit" in message:
        return f"{service} временно ограничил число запросов (HTTP 429)"
    if status in {401, 403} or "authentication" in name or "permission" in name:
        return f"{service} отклонил авторизацию или доступ (HTTP {status or '401/403'})"
    if "timeout" in name or "timed out" in message:
        return "сервис не ответил вовремя"
    if "readerror" in chain_names:
        return f"соединение с {service} оборвалось при чтении ответа"
    if "connecterror" in chain_names or "apiconnectionerror" in chain_names:
        return f"не удалось установить соединение с {service}"
    if status and status >= 500:
        return f"{service} временно недоступен (HTTP {status})"
    if status:
        suffix = f": {detail}" if detail else ""
        return f"{service} отклонил запрос (HTTP {status}){suffix}"
    if "telegram" in name or "bad request" in message:
        return "Telegram не смог скачать или отправить данные"
    if detail:
        return f"ошибка {type(exc).__name__}: {detail}"
    return f"неизвестная ошибка {type(exc).__name__}"


def _exception_chain(exc: Exception):
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def media_identity(message, kind: str) -> str:
    document = getattr(message, "document", None)
    audio = getattr(message, "audio", None)
    filename = getattr(document, "file_name", None) or getattr(audio, "file_name", None)
    if filename:
        return f"{kind} «{html.escape(filename)}»"
    return f"{kind} в сообщении №{message.message_id}"


def message_link(chat_id: int, message_id: int) -> str | None:
    value = str(chat_id)
    if not value.startswith("-100") or message_id <= 0:
        return None
    return f"https://t.me/c/{value[4:]}/{message_id}"


class ErrorReporter:
    def __init__(self, bot, admin_id: int, cooldown_seconds: int = 3600):
        self.bot = bot
        self.admin_id = admin_id
        self.cooldown_seconds = cooldown_seconds
        self._sent: dict[str, float] = {}

    async def notify(self, key: str, text: str) -> bool:
        now = time.monotonic()
        if now - self._sent.get(key, 0) < self.cooldown_seconds:
            return False
        await self.bot.send_message(self.admin_id, text)
        self._sent[key] = now
        return True

    async def media(self, message, kind: str, stage: str, exc: Exception):
        title = html.escape(message.chat.title or str(message.chat.id))
        topic = message.message_thread_id or "без темы"
        link = message_link(message.chat.id, message.message_id)
        source = f'\n<a href="{link}">Открыть исходное сообщение</a>' if link else ""
        text = (
            "⚠️ <b>Сообщение от бота-суммаризатора</b>\n"
            f"Что не получилось: не удалось {html.escape(stage)}.\n"
            f"Что обрабатывалось: {media_identity(message, kind)}.\n"
            f"Где: группа «{title}», тема {topic}\n"
            f"Причина: {html.escape(human_reason(exc, 'Telegram' if 'Telegram' in stage else 'AI-сервис'))} после трёх попыток.\n"
            "Последствия: только этот файл не попадёт в сводку; остальная переписка собирается.\n"
            f"Что делать: отправь файл повторно, если он важен для сводки.{source}"
        )
        await self.notify(f"media:{message.chat.id}:{message.message_id}", text)

    async def summary(self, group, thread_id: int, exc: Exception):
        title = html.escape(group["title"])
        text = (
            "🟠 <b>Сообщение от бота-суммаризатора</b>\n"
            "Бот не смог создать автоматическую сводку переписки.\n"
            f"Где: группа «{title}», тема {thread_id or 'без отдельной темы'}\n"
            f"Причина: {human_reason(exc)} после трёх попыток.\n"
            "Последствия: сообщения сохранены; остальные темы продолжают обрабатываться.\n"
            "Что делать: ничего — бот повторит попытку при следующем запуске."
        )
        await self.notify(f"summary:{group['chat_id']}:{thread_id}:{type(exc).__name__}", text)
