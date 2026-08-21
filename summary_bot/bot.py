from datetime import datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatMemberStatus, ParseMode
from aiogram.filters import Command
from aiogram.types import BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from summary_bot.imports import import_metadata, import_payload, imported_message_id
from summary_bot.service import period_start


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


def import_controls(token: str):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Завершить и сделать саммари", callback_data=f"import_finish:{token}"),
        InlineKeyboardButton(text="❌ Отменить", callback_data=f"import_cancel:{token}"),
    ]])


def build_dispatcher(db, service, admin_id: int, media=None):
    router, dp = Router(), Dispatcher()
    warned_empty_imports: set[str] = set()
    warned_old_imports: set[str] = set()

    @router.message(Command("start"))
    async def start(m: Message):
        if m.chat.type == "private" and m.from_user.id == admin_id:
            parts = (m.text or "").split(maxsplit=1)
            if len(parts) == 2 and parts[1].startswith("import_"):
                token = parts[1].removeprefix("import_")
                session = await db.get_import_session(token, admin_id)
                if not session:
                    return await m.answer("Сессия импорта не найдена или уже завершена.")
                group = await db.get_group(session["chat_id"])
                return await m.answer(
                    f"Импорт для группы «{group['title']}» открыт.\n\n"
                    "1. Вернись в нужную тему группы.\n"
                    "2. Выдели старые сообщения и перешли их сюда. Можно сразу несколько.\n"
                    "3. Вернись сюда и нажми «Завершить и сделать саммари».\n\n"
                    "Бот принимает текст, фотографии, голосовые сообщения и аудиофайлы. "
                    "Изображения распознаются, аудио переводится в текст.",
                    reply_markup=import_controls(token),
                )
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
        is_group = m.chat.type in {"group", "supergroup"}
        if len(parts) == 1 and is_group:
            chat_id = m.chat.id
        elif len(parts) == 2:
            try:
                chat_id = int(parts[1])
            except ValueError:
                return await m.answer(f"Формат: /{action} CHAT_ID")
        else:
            return await m.answer(
                f"Выполни /{action} в нужной группе или укажи её ID: /{action} CHAT_ID"
            )
        group = await db.get_group(chat_id)
        if not group: return await m.answer("Группа не найдена.")
        if action == "settings": return await m.answer(f"{group['title']}\nСтатус: {group['status']}\nРежим: {group['period']}")
        if action == "pause": await db.set_status(chat_id, "paused")
        if action == "resume": await db.set_status(chat_id, "active")
        if action == "disconnect": await db.disconnect(chat_id)
        if action == "summary_now":
            if group["status"] != "active" or not group["period"]:
                return await m.answer("Группа ещё не активирована или период не выбран.")
            count = await service.run_group(chat_id, group["period"])
            if count == 0:
                labels = {"day": "24 часа", "week": "7 дней", "month": "30 дней"}
                return await m.answer(
                    f"За последние {labels[group['period']]} новых сообщений для сводки нет. "
                    "Бот видит только сообщения, полученные после подключения группы."
                )
            return await m.answer(f"Саммари готово. Опубликовано тем: {count}")
        await m.answer("Готово.")

    @router.message(Command("import_history"))
    async def import_history(m: Message):
        if m.from_user.id != admin_id: return
        if m.chat.type not in {"group", "supergroup"}:
            return await m.answer("Запусти эту команду внутри нужной группы и темы.")
        group = await db.get_group(m.chat.id)
        if not group or group["status"] != "active" or not group["period"]:
            return await m.answer("Сначала подключи группу и выбери период саммари.")
        token = await db.create_import_session(admin_id, m.chat.id, m.message_thread_id or 0)
        me = await m.bot.get_me()
        url = f"https://t.me/{me.username}?start=import_{token}"
        keyboard = InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="📥 Переслать старые сообщения", url=url)
        ]])
        await m.answer(
            "Импорт привязан к этой группе и теме. Открой личный чат по кнопке и перешли сообщения.",
            reply_markup=keyboard,
        )

    @router.message(F.chat.type == "private")
    async def collect_import(m: Message):
        if m.from_user.id != admin_id: return
        session = await db.active_import_session(admin_id)
        if not session: return
        is_supported_media = bool(
            m.photo or m.voice or m.audio
            or (m.document and (m.document.mime_type or "").startswith("image/"))
        )
        payload = None if is_supported_media else import_payload(m)
        if is_supported_media and media:
            sent_at, sender = import_metadata(m)
            text = await media_text(m)
            if text:
                payload = sent_at, sender, text
        if not payload:
            if session["token"] not in warned_empty_imports:
                warned_empty_imports.add(session["token"])
                return await m.answer(
                    "Этот тип сообщения пока не поддерживается. Пришли текст, фотографию, "
                    "голосовое сообщение или аудиофайл."
                )
            return
        sent_at, sender, text = payload
        group = await db.get_group(session["chat_id"])
        now = datetime.now(sent_at.tzinfo) if sent_at.tzinfo else datetime.now()
        if sent_at < period_start(group["period"], now):
            if session["token"] not in warned_old_imports:
                warned_old_imports.add(session["token"])
                labels = {"day": "24 часов", "week": "7 дней", "month": "30 дней"}
                return await m.answer(
                    f"Сообщения старше {labels[group['period']]} пропускаются согласно настройкам группы. "
                    "Продолжай пересылать более новые сообщения."
                )
            return
        message_id = imported_message_id(session["chat_id"], sent_at, sender, text)
        inserted = await db.add_imported_message(
            session["token"], session["chat_id"], message_id, session["thread_id"],
            sender, text, sent_at,
        )
        if inserted and session["imported_count"] == 0:
            await m.answer(
                "✅ Первое сообщение принято. Продолжай пересылать остальные, а когда закончишь — "
                "нажми кнопку ниже.",
                reply_markup=import_controls(session["token"]),
            )

    @router.callback_query(F.data.startswith("import_cancel:"))
    async def cancel_import(c: CallbackQuery):
        if c.from_user.id != admin_id: return await c.answer("Недоступно", show_alert=True)
        token = c.data.split(":", 1)[1]
        session = await db.get_import_session(token, admin_id)
        if not session: return await c.answer("Сессия уже закрыта", show_alert=True)
        await db.close_import_session(token, "cancelled")
        warned_empty_imports.discard(token); warned_old_imports.discard(token)
        await c.message.edit_text("Импорт отменён."); await c.answer()

    @router.callback_query(F.data.startswith("import_finish:"))
    async def finish_import(c: CallbackQuery):
        if c.from_user.id != admin_id: return await c.answer("Недоступно", show_alert=True)
        token = c.data.split(":", 1)[1]
        session = await db.get_import_session(token, admin_id)
        if not session: return await c.answer("Сессия уже закрыта", show_alert=True)
        group = await db.get_group(session["chat_id"])
        await c.message.edit_text(
            f"Принято сообщений: {session['imported_count']}. Создаю саммари для «{group['title']}»…"
        )
        count = await service.run_group(session["chat_id"], group["period"])
        await db.close_import_session(token)
        warned_empty_imports.discard(token); warned_old_imports.discard(token)
        await c.message.edit_text(
            f"Импорт завершён. Принято сообщений: {session['imported_count']}. Опубликовано тем: {count}."
        )
        await c.answer()

    for command in ("settings", "pause", "resume", "summary_now", "disconnect"):
        router.message.register(lambda m, a=command: admin_command(m, a), Command(command))

    async def media_text(m: Message) -> str | None:
        try:
            if m.photo:
                data = await m.bot.download(m.photo[-1])
                description = await media.describe_image(data.read(), "image/jpeg", m.caption)
                return f"[Изображение] {description}" if description else None
            document = m.document
            if document and (document.mime_type or "").startswith("image/"):
                data = await m.bot.download(document)
                description = await media.describe_image(
                    data.read(), document.mime_type or "image/jpeg", m.caption,
                )
                return f"[Изображение] {description}" if description else None
            audio = m.voice or m.audio
            if audio:
                if (audio.file_size or 0) > 10 * 1024 * 1024 or (audio.duration or 0) > 300:
                    return "[Аудиозапись длиннее 5 минут — автоматическая расшифровка пропущена]"
                data = await m.bot.download(audio)
                filename = getattr(audio, "file_name", None) or (
                    "voice.ogg" if m.voice else "audio.mp3"
                )
                mime_type = getattr(audio, "mime_type", None) or (
                    "audio/ogg" if m.voice else "audio/mpeg"
                )
                transcript = await media.transcribe_audio(data.read(), filename, mime_type)
                prefix = f"Подпись: {m.caption}\n" if m.caption else ""
                return f"[Расшифровка аудио] {prefix}{transcript}" if transcript else None
        except Exception:
            import logging
            logging.exception("Failed to process Telegram media")
            try:
                await m.bot.send_message(
                    admin_id,
                    "Не удалось обработать медиа. Это сообщение пропущено; "
                    "остальная переписка продолжает собираться.",
                )
            except Exception:
                pass
        return None

    @router.message(F.chat.type.in_({"group", "supergroup"}))
    async def collect(m: Message):
        group = await db.get_group(m.chat.id)
        if not group or group["status"] != "active" or not m.from_user or m.from_user.is_bot: return
        text = m.text or m.caption
        if media and (
            m.photo or m.voice or m.audio
            or (m.document and (m.document.mime_type or "").startswith("image/"))
        ):
            text = await media_text(m)
        if not text:
            return
        thread_name = m.reply_to_message.forum_topic_created.name if m.reply_to_message and m.reply_to_message.forum_topic_created else None
        await db.add_message(m.chat.id, m.message_id, m.message_thread_id, thread_name,
                             m.from_user.full_name, text, m.date)

    dp.include_router(router)
    return dp


async def set_commands(bot: Bot):
    await bot.set_my_commands([BotCommand(command=x, description=d) for x,d in [
        ("settings","Настройки группы"),("pause","Приостановить"),("resume","Возобновить"),
        ("summary_now","Саммари сейчас"),("import_history","Импорт старых сообщений"),
        ("disconnect","Отключить группу")]])
