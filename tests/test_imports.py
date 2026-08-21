from datetime import datetime, timezone
from types import SimpleNamespace

from summary_bot.imports import forwarded_payload, imported_message_id


def test_forwarded_payload_and_stable_id():
    sent_at = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
    message = SimpleNamespace(
        forward_origin=SimpleNamespace(
            date=sent_at,
            sender_user=SimpleNamespace(full_name="Иван Иванов"),
            sender_chat=None,
            chat=None,
            sender_user_name=None,
            author_signature=None,
        ),
        text="Согласовали запуск",
        caption=None,
    )
    assert forwarded_payload(message) == (sent_at, "Иван Иванов", "Согласовали запуск")
    first = imported_message_id(-100123, sent_at, "Иван Иванов", "Согласовали запуск")
    second = imported_message_id(-100123, sent_at, "Иван Иванов", "Согласовали запуск")
    assert first == second and first < 0


def test_non_forwarded_message_is_rejected():
    message = SimpleNamespace(forward_origin=None, text="Обычное сообщение", caption=None)
    assert forwarded_payload(message) is None
