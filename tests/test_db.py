import pytest
from datetime import datetime, timedelta

from summary_bot.db import Database


@pytest.mark.asyncio
async def test_activation_and_delete(tmp_path):
    db = Database(str(tmp_path / "bot.db")); await db.init()
    await db.upsert_group(-100123, "Test")
    assert (await db.get_group(-100123))["status"] == "pending"
    await db.set_period(-100123, "day")
    row = await db.get_group(-100123)
    assert row["status"] == "active" and row["period"] == "day"

    token = await db.create_import_session(127626487, -100123, 42)
    session = await db.get_import_session(token, 127626487)
    assert session["chat_id"] == -100123 and session["thread_id"] == 42
    now = datetime.now()
    inserted = await db.add_imported_message(
        token, -100123, -10, 42, "Иван", "Старое сообщение", now
    )
    duplicate = await db.add_imported_message(
        token, -100123, -10, 42, "Иван", "Старое сообщение", now
    )
    assert inserted is True
    assert duplicate is False
    session = await db.active_import_session(127626487)
    assert session["imported_count"] == 1
    await db.close_import_session(token, "cancelled")
    assert await db.active_import_session(127626487) is None
    assert await db.message_threads(-100123, now - timedelta(days=1)) == {}
