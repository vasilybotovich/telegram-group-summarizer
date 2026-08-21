import asyncio
import logging

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from summary_bot.bot import build_dispatcher, set_commands
from summary_bot.config import Settings
from summary_bot.db import Database
from summary_bot.service import SummaryService
from summary_bot.summarizer import Summarizer


async def main():
    settings = Settings()
    logging.basicConfig(level=logging.INFO)
    db = Database(settings.database_path); await db.init()
    bot = Bot(settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    summarizer = Summarizer(settings.dashscope_api_key, settings.dashscope_base_url, settings.qwen_model)
    service = SummaryService(bot, db, summarizer, settings.admin_user_id, settings.tz)
    dp = build_dispatcher(db, service, settings.admin_user_id)
    scheduler = AsyncIOScheduler(timezone=settings.tz)
    scheduler.add_job(service.run_due, "cron", minute=0, id="summary_due", max_instances=1)
    scheduler.start(); await set_commands(bot)
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__": asyncio.run(main())
