import pytest

from summary_bot.db import Database


@pytest.mark.asyncio
async def test_activation_and_delete(tmp_path):
    db = Database(str(tmp_path / "bot.db")); await db.init()
    await db.upsert_group(-100123, "Test")
    assert (await db.get_group(-100123))["status"] == "pending"
    await db.set_period(-100123, "day")
    row = await db.get_group(-100123)
    assert row["status"] == "active" and row["period"] == "day"
