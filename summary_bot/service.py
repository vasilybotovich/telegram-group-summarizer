from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def period_start(period: str, now: datetime) -> datetime:
    if period == "day": return now - timedelta(days=1)
    if period == "week": return now - timedelta(days=7)
    if period == "month":
        first = now.replace(day=1)
        previous_last = first - timedelta(days=1)
        return previous_last.replace(day=1)
    raise ValueError(period)


def is_due(period: str, now: datetime) -> bool:
    if now.hour != 20 or now.minute != 0: return False
    if period == "day": return True
    if period == "week": return now.weekday() == 4
    if period == "month": return (now + timedelta(days=1)).month != now.month
    return False


class SummaryService:
    def __init__(self, bot, db, summarizer, admin_id: int, tz="Europe/Moscow"):
        self.bot, self.db, self.summarizer, self.admin_id = bot, db, summarizer, admin_id
        self.zone = ZoneInfo(tz)

    async def run_due(self):
        now = datetime.now(self.zone).replace(second=0, microsecond=0)
        for group in await self.db.groups("active"):
            if is_due(group["period"], now):
                await self.run_group(group["chat_id"], group["period"], now)

    async def run_group(self, chat_id: int, period: str | None = None, now: datetime | None = None):
        group = await self.db.get_group(chat_id)
        if not group or group["status"] != "active": return 0
        now = now or datetime.now(self.zone)
        since = period_start(period or group["period"], now)
        threads = await self.db.message_threads(chat_id, since)
        published = 0
        try:
            for thread_id, rows in threads.items():
                text = await self.summarizer.summarize(chat_id, rows)
                await self.bot.send_message(chat_id, "📝 <b>Главное за период</b>\n\n" + text,
                                            message_thread_id=thread_id or None)
                published += 1
            if published:
                await self.db.finish_summary(chat_id, now)
            return published
        except Exception as exc:
            await self.bot.send_message(self.admin_id, f"Не удалось создать саммари для «{group['title']}»: {type(exc).__name__}")
            raise
