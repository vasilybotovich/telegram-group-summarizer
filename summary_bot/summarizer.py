from __future__ import annotations

import html
import re

from openai import AsyncOpenAI


SYSTEM = """Ты редактор Telegram-дайджестов. Выдели только существенные итоги обсуждения.
Пиши кратко по-русски, без вводных фраз, домыслов и технических подробностей о своей работе.
Не перечисляй приветствия, мелкие реплики и повторы. Не называй функцию командой, если это кнопка.

Верни только строки следующего формата, без Markdown и без нумерации:
Короткий заголовок || Конкретный итог, решение, вопрос или полезный факт || номера источников через запятую

Пример:
Срок запуска || Запуск согласован на следующую среду || 2,5

Используй только номера источников из входных данных. Для каждого пункта укажи 1–3 самых
релевантных источника. Не вставляй URL, даты, квадратные скобки, звёздочки и служебный текст."""


class Summarizer:
    def __init__(self, api_key: str, base_url: str, model: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def summarize(self, chat_id: int, rows) -> str:
        numbered = list(enumerate(rows, start=1))
        chunks, current, size = [], [], 0
        for source_no, row in numbered:
            line = (
                f"ИСТОЧНИК {source_no}\n"
                f"Дата: {row['sent_at']}\n"
                f"Автор: {row['sender_name'] or 'Участник'}\n"
                f"Текст: {row['text']}"
            )
            if size + len(line) > 50000 and current:
                chunks.append("\n\n".join(current)); current, size = [], 0
            current.append(line); size += len(line)
        if current:
            chunks.append("\n\n".join(current))

        raw_parts = [await self._ask(chunk) for chunk in chunks]
        links = self._source_links(chat_id, numbered)
        return self._render("\n".join(raw_parts), links)

    @staticmethod
    def _source_links(chat_id: int, numbered) -> dict[int, str]:
        internal_id = str(chat_id)[4:] if str(chat_id).startswith("-100") else str(chat_id).lstrip("-")
        return {
            source_no: f"https://t.me/c/{internal_id}/{row['message_id']}"
            for source_no, row in numbered
            if row["message_id"] > 0
        }

    @staticmethod
    def _render(raw: str, links: dict[int, str]) -> str:
        items = []
        for line in raw.splitlines():
            parts = [part.strip() for part in line.strip().lstrip("-•0123456789. ").split("||")]
            if len(parts) < 2 or not parts[0] or not parts[1]:
                continue
            source_ids = []
            if len(parts) >= 3:
                source_ids = [int(value) for value in re.findall(r"\d+", parts[2])]
            source_links = []
            for source_id in source_ids:
                url = links.get(source_id)
                if url and url not in source_links:
                    source_links.append(url)
            references = " · ".join(
                f'<a href="{url}">↗ источник {index}</a>'
                for index, url in enumerate(source_links, start=1)
            )
            body = f"• <b>{html.escape(parts[0])}</b> — {html.escape(parts[1])}"
            if references:
                body += f"\n  {references}"
            items.append(body)
        if items:
            return "\n\n".join(items)
        return "• Существенных итогов за выбранный период не найдено."

    async def _ask(self, text: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": text}],
            temperature=0.1,
            max_tokens=1600,
        )
        return response.choices[0].message.content.strip()
