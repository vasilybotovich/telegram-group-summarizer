from __future__ import annotations

import hashlib


def forwarded_payload(message):
    """Return original date, visible sender and text for a forwarded message."""
    origin = getattr(message, "forward_origin", None)
    text = getattr(message, "text", None) or getattr(message, "caption", None)
    if origin is None or not text:
        return None

    user = getattr(origin, "sender_user", None)
    chat = getattr(origin, "sender_chat", None) or getattr(origin, "chat", None)
    sender = (
        getattr(user, "full_name", None)
        or getattr(origin, "sender_user_name", None)
        or getattr(chat, "title", None)
        or getattr(origin, "author_signature", None)
        or "Участник"
    )
    return origin.date, sender, text


def imported_message_id(chat_id: int, sent_at, sender: str, text: str) -> int:
    """Stable negative ID keeps imports deduplicated without colliding with Telegram IDs."""
    raw = f"{chat_id}\0{sent_at.isoformat()}\0{sender}\0{text}".encode()
    value = int.from_bytes(hashlib.sha256(raw).digest()[:8], "big") & ((1 << 63) - 1)
    return -(value or 1)
