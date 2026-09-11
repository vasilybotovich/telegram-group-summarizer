from __future__ import annotations

import asyncio
import html
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


def human_reason(exc: Exception) -> str:
    status = getattr(exc, "status_code", None)
    name = type(exc).__name__.lower()
    message = str(exc).lower()
    if status == 429 or "rate limit" in message:
        return "сервис временно ограничил число запросов"
    if status in {401, 403} or "authentication" in name or "permission" in name:
        return "сервис отклонил авторизацию или доступ"
    if "timeout" in name or "timed out" in message:
        return "сервис не ответил вовремя"
    if status and status >= 500:
        return "внешний сервис временно недоступен"
    if "telegram" in name or "bad request" in message:
        return "Telegram не смог скачать или отправить данные"
    return "не удалось получить ответ от сервиса обработки"


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

    async def media(self, message, kind: str, exc: Exception):
        title = html.escape(message.chat.title or str(message.chat.id))
        topic = message.message_thread_id or "без темы"
        link = message_link(message.chat.id, message.message_id)
        source = f'\n<a href="{link}">Открыть исходное сообщение</a>' if link else ""
        text = (
            "⚠️ <b>Сообщение от бота-суммаризатора</b>\n"
            f"Бот не смог обработать {html.escape(kind)} для будущей сводки переписки.\n"
            f"Где: группа «{title}», тема {topic}\n"
            f"Причина: {human_reason(exc)} после трёх попыток.\n"
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
