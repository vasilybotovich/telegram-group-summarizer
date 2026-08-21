from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime

import aiosqlite


SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER NOT NULL);
INSERT INTO schema_version(version) SELECT 1 WHERE NOT EXISTS(SELECT 1 FROM schema_version);
CREATE TABLE IF NOT EXISTS groups(
  chat_id INTEGER PRIMARY KEY, title TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
  period TEXT, added_at TEXT NOT NULL, approved_at TEXT, last_summary_at TEXT
);
CREATE TABLE IF NOT EXISTS messages(
  chat_id INTEGER NOT NULL, message_id INTEGER NOT NULL, thread_id INTEGER NOT NULL DEFAULT 0,
  thread_name TEXT, sender_name TEXT, text TEXT NOT NULL, sent_at TEXT NOT NULL,
  PRIMARY KEY(chat_id,message_id), FOREIGN KEY(chat_id) REFERENCES groups(chat_id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS ix_messages_scope ON messages(chat_id,thread_id,sent_at);
"""


class Database:
    def __init__(self, path: str):
        self.path = path

    @asynccontextmanager
    async def connect(self):
        db = await aiosqlite.connect(self.path)
        try:
            await db.execute("PRAGMA foreign_keys=ON")
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("PRAGMA busy_timeout=5000")
            db.row_factory = aiosqlite.Row
            yield db
        finally:
            await db.close()

    async def init(self):
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        async with self.connect() as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def upsert_group(self, chat_id: int, title: str):
        async with self.connect() as db:
            await db.execute(
                "INSERT INTO groups(chat_id,title,added_at) VALUES(?,?,?) "
                "ON CONFLICT(chat_id) DO UPDATE SET title=excluded.title",
                (chat_id, title, datetime.utcnow().isoformat()),
            )
            await db.commit()

    async def set_period(self, chat_id: int, period: str):
        async with self.connect() as db:
            await db.execute(
                "UPDATE groups SET status='active',period=?,approved_at=? WHERE chat_id=?",
                (period, datetime.utcnow().isoformat(), chat_id),
            )
            await db.commit()

    async def set_status(self, chat_id: int, status: str):
        async with self.connect() as db:
            await db.execute("UPDATE groups SET status=? WHERE chat_id=?", (status, chat_id))
            await db.commit()

    async def get_group(self, chat_id: int):
        async with self.connect() as db:
            cur = await db.execute("SELECT * FROM groups WHERE chat_id=?", (chat_id,))
            return await cur.fetchone()

    async def groups(self, status: str | None = None):
        async with self.connect() as db:
            query, args = "SELECT * FROM groups", ()
            if status:
                query, args = query + " WHERE status=?", (status,)
            cur = await db.execute(query, args)
            return await cur.fetchall()

    async def add_message(self, chat_id, message_id, thread_id, thread_name, sender, text, sent_at):
        async with self.connect() as db:
            await db.execute(
                "INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?,?,?)",
                (chat_id, message_id, thread_id or 0, thread_name, sender, text, sent_at.isoformat()),
            )
            await db.commit()

    async def message_threads(self, chat_id: int, since: datetime):
        async with self.connect() as db:
            cur = await db.execute(
                "SELECT * FROM messages WHERE chat_id=? AND sent_at>=? ORDER BY thread_id,sent_at",
                (chat_id, since.isoformat()),
            )
            rows = await cur.fetchall()
        result = {}
        for row in rows:
            result.setdefault(row["thread_id"], []).append(row)
        return result

    async def finish_summary(self, chat_id: int, through: datetime):
        async with self.connect() as db:
            await db.execute("DELETE FROM messages WHERE chat_id=? AND sent_at<=?", (chat_id, through.isoformat()))
            await db.execute("UPDATE groups SET last_summary_at=? WHERE chat_id=?", (through.isoformat(), chat_id))
            await db.commit()

    async def disconnect(self, chat_id: int):
        async with self.connect() as db:
            await db.execute("DELETE FROM groups WHERE chat_id=?", (chat_id,))
            await db.commit()
