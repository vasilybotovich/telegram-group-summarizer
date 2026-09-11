from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from summary_bot.errors import ErrorReporter, retry


def period_start(period: str, now: datetime) -> datetime:
    if period == "day": return now - timedelta(days=1)
    if period == "week": return now - timedelta(days=7)
    if period == "month": return now - timedelta(days=30)
    raise ValueError(period)


def period_label(period: str) -> str:
    return {"day": "24 часа", "week": "7 дней", "month": "30 дней"}[period]


def is_due(period: str, now: datetime) -> bool:
    if now.hour != 20 or now.minute != 0: return False
    if period == "day": return True
    if period == "week": return now.weekday() == 4
    if period == "month": return (now + timedelta(days=1)).month != now.month
    return False


class SummaryService:
    def __init__(
        self, bot, db, summarizer, admin_id: int, tz="Europe/Moscow",
        excluded_thread_ids: set[int] | None = None,
    ):
        self.bot, self.db, self.summarizer, self.admin_id = bot, db, summarizer, admin_id
        self.zone = ZoneInfo(tz)
        self.excluded_thread_ids = excluded_thread_ids or set()
        self.reporter = ErrorReporter(bot, admin_id)

    async def run_due(self):
        now = datetime.now(self.zone).replace(second=0, microsecond=0)
        for group in await self.db.groups("active"):
            if is_due(group["period"], now):
                try:
                    await self.run_group(group["chat_id"], group["period"], now)
                except Exception:
                    import logging
                    logging.exception("Failed to run summary group %s", group["chat_id"])

    async def run_group(self, chat_id: int, period: str | None = None, now: datetime | None = None):
        group = await self.db.get_group(chat_id)
        if not group or group["status"] != "active": return 0
        now = now or datetime.now(self.zone)
        selected_period = period or group["period"]
        since = period_start(selected_period, now)
        threads = await self.db.message_threads(chat_id, since)
        published = 0
        for thread_id, rows in threads.items():
            if thread_id in self.excluded_thread_ids:
                continue
            try:
                async def publish():
                    text = await self.summarizer.summarize(chat_id, rows)
                    await self.bot.send_message(
                        chat_id,
                        "📝 <b>Автоматическая сводка переписки</b>\n"
                        f"Главное за {period_label(selected_period)} в этой теме:\n\n" + text,
                        message_thread_id=thread_id or None,
                    )
                await retry(publish)
                published += 1
                await self.db.finish_thread(chat_id, thread_id, now)
            except Exception as exc:
                import logging
                logging.exception("Failed to summarize chat=%s thread=%s", chat_id, thread_id)
                try:
                    await self.reporter.summary(group, thread_id, exc)
                except Exception:
                    logging.exception("Failed to notify administrator")
        return published
