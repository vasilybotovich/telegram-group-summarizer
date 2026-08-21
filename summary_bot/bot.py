from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message


def kb(chat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Одобрить", callback_data=f"approve:{chat_id}"),
         InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{chat_id}")]
    ])


def periods(chat_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="День", callback_data=f"period:{chat_id}:day"),
        InlineKeyboardButton(text="Неделя", callback_data=f"period:{chat_id}:week"),
        InlineKeyboardButton(text="Месяц", callback_data=f"period:{chat_id}:month"),
    ]])


def build_dispatcher(db, service, admin_id: int):
    router, dp = Router(), Dispatcher()

    @router.message(Command("start"))
    async def start(m: Message):
        if m.chat.type == "private" and m.from_user.id == admin_id:
            await m.answer("Готов к работе. Запросы на подключение групп будут приходить сюда.")

    @router.my_chat_member()
    async def membership(event):
        if event.chat.type not in {"group", "supergroup"}: return
        if event.new_chat_member.status in {ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR}:
            await db.upsert_group(event.chat.id, event.chat.title or str(event.chat.id))
            try:
                await event.bot.send_message(admin_id, f"Меня добавили в группу «{event.chat.title}». Начать работу?", reply_markup=kb(event.chat.id))
            except Exception:
                await event.bot.send_message(event.chat.id, "Сергей, сначала откройте личный чат со мной и нажмите /start, затем добавьте меня повторно.")

    @router.callback_query(F.data.startswith("approve:"))
    async def approve(c: CallbackQuery):
        if c.from_user.id != admin_id: return await c.answer("Недоступно", show_alert=True)
        chat_id = int(c.data.split(":")[1])
        await c.message.edit_text("Как часто создавать саммари?", reply_markup=periods(chat_id)); await c.answer()

    @router.callback_query(F.data.startswith("reject:"))
    async def reject(c: CallbackQuery):
        if c.from_user.id != admin_id: return await c.answer("Недоступно", show_alert=True)
        chat_id = int(c.data.split(":")[1]); await db.set_status(chat_id, "rejected")
        await c.message.edit_text("Группа отклонена. Сообщения не собираются."); await c.answer()

    @router.callback_query(F.data.startswith("period:"))
    async def choose_period(c: CallbackQuery):
        if c.from_user.id != admin_id: return await c.answer("Недоступно", show_alert=True)
        _, cid, period = c.data.split(":"); await db.set_period(int(cid), period)
        labels = {"day":"ежедневно", "week":"по пятницам", "month":"в последний день месяца"}
        await c.message.edit_text(f"Подключено: {labels[period]} в 20:00 мск. Сбор сообщений начат."); await c.answer()

    async def admin_command(m: Message, action: str):
        if m.from_user.id != admin_id: return
        parts = (m.text or "").split()
        if len(parts) != 2: return await m.answer(f"Формат: /{action} CHAT_ID")
        chat_id = int(parts[1]); group = await db.get_group(chat_id)
        if not group: return await m.answer("Группа не найдена.")
        if action == "settings": return await m.answer(f"{group['title']}\nСтатус: {group['status']}\nРежим: {group['period']}")
        if action == "pause": await db.set_status(chat_id, "paused")
        if action == "resume": await db.set_status(chat_id, "active")
        if action == "disconnect": await db.disconnect(chat_id)
        if action == "summary_now":
            count = await service.run_group(chat_id); return await m.answer(f"Опубликовано тем: {count}")
        await m.answer("Готово.")

    for command in ("settings", "pause", "resume", "summary_now", "disconnect"):
        router.message.register(lambda m, a=command: admin_command(m, a), Command(command))

    @router.message(F.chat.type.in_({"group", "supergroup"}), F.text)
    async def collect(m: Message):
        group = await db.get_group(m.chat.id)
        if not group or group["status"] != "active" or m.from_user.is_bot: return
        thread_name = m.reply_to_message.forum_topic_created.name if m.reply_to_message and m.reply_to_message.forum_topic_created else None
        await db.add_message(m.chat.id, m.message_id, m.message_thread_id, thread_name,
                             m.from_user.full_name, m.text, m.date)

    dp.include_router(router)
    return dp


async def set_commands(bot: Bot):
    await bot.set_my_commands([BotCommand(command=x, description=d) for x,d in [
        ("settings","Настройки группы"),("pause","Приостановить"),("resume","Возобновить"),
        ("summary_now","Саммари сейчас"),("disconnect","Отключить группу")]])
