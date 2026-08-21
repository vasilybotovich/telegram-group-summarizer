from openai import AsyncOpenAI


SYSTEM = """Ты редактор Telegram-дайджестов. Выдели только существенные итоги обсуждения.
Пиши кратко по-русски, без вводных фраз и домыслов. Каждый пункт должен содержать конкретный итог,
решение, важный вопрос или полезный факт. Добавляй ссылки на исходные сообщения, когда они доступны.
Не перечисляй мелкие реплики, приветствия и повторы. Формат: маркированный список."""


class Summarizer:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def summarize(self, chat_id: int, rows) -> str:
        chunks, current, size = [], [], 0
        for row in rows:
            link_id = str(chat_id)[4:] if str(chat_id).startswith("-100") else str(chat_id).lstrip("-")
            link = f"https://t.me/c/{link_id}/{row['message_id']}" if row["message_id"] > 0 else None
            suffix = f" ({link})" if link else ""
            line = f"[{row['sent_at']}] {row['sender_name'] or 'Участник'}: {row['text']}{suffix}"
            if size + len(line) > 50000 and current:
                chunks.append("\n".join(current)); current, size = [], 0
            current.append(line); size += len(line)
        if current:
            chunks.append("\n".join(current))
        partials = [await self._ask(c) for c in chunks]
        return partials[0] if len(partials) == 1 else await self._ask("Объедини частичные выжимки:\n" + "\n".join(partials))

    async def _ask(self, text: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
            temperature=0.2,
            max_tokens=1600,
        )
        return response.choices[0].message.content.strip()
