from datetime import datetime
from zoneinfo import ZoneInfo

from summary_bot.service import is_due, period_label, period_start


TZ = ZoneInfo("Europe/Moscow")


def test_schedules():
    assert is_due("day", datetime(2026, 8, 20, 20, 0, tzinfo=TZ))
    assert is_due("week", datetime(2026, 8, 21, 20, 0, tzinfo=TZ))
    assert not is_due("week", datetime(2026, 8, 20, 20, 0, tzinfo=TZ))
    assert is_due("month", datetime(2026, 8, 31, 20, 0, tzinfo=TZ))
    assert not is_due("month", datetime(2026, 8, 30, 20, 0, tzinfo=TZ))


def test_period_windows():
    now = datetime(2026, 8, 31, 20, 0, tzinfo=TZ)
    assert period_start("day", now).date().isoformat() == "2026-08-30"
    assert period_start("week", now).date().isoformat() == "2026-08-24"
    assert period_start("month", now).date().isoformat() == "2026-08-01"
    assert period_label("day") == "24 часа"
    assert period_label("week") == "7 дней"
    assert period_label("month") == "30 дней"
