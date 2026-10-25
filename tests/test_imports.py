from datetime import datetime, timezone
from types import SimpleNamespace

from summary_bot.imports import import_metadata, import_payload, imported_message_id, message_text


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
    assert import_payload(message) == (sent_at, "Иван Иванов", "Согласовали запуск")
    first = imported_message_id(-100123, sent_at, "Иван Иванов", "Согласовали запуск")
    second = imported_message_id(-100123, sent_at, "Иван Иванов", "Согласовали запуск")
    assert first == second and first < 0


def test_plain_text_can_be_imported_manually():
    sent_at = datetime(2026, 8, 20, 10, 0, tzinfo=timezone.utc)
    message = SimpleNamespace(
        forward_origin=None,
        text="Вставленный текст",
        caption=None,
        date=sent_at,
        from_user=SimpleNamespace(full_name="Сергей"),
    )
    assert import_payload(message) == (sent_at, "Сергей", "Вставленный текст")


def test_media_without_caption_is_skipped():
    message = SimpleNamespace(forward_origin=SimpleNamespace(), text=None, caption=None)
    assert import_payload(message) is None


def test_forwarded_media_metadata_without_caption():
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
    )
    assert import_metadata(message) == (sent_at, "Иван Иванов")


def test_attachment_without_text_is_ignored_without_inspection():
    message = SimpleNamespace(
        text=None,
        caption=None,
        photo=[object()],
        voice=object(),
        audio=object(),
        video=object(),
        document=object(),
    )
    assert message_text(message) is None


def test_only_attachment_caption_is_collected():
    message = SimpleNamespace(text=None, caption="Описание вложения", photo=[object()])
    assert message_text(message) == "Описание вложения"


def test_whitespace_only_text_is_ignored():
    message = SimpleNamespace(text="   ", caption=None)
    assert message_text(message) is None
