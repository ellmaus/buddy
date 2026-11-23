import os
import time

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    task_title TEXT NOT NULL,
    step_idx INTEGER NOT NULL DEFAULT 0,
    step_text TEXT NOT NULL,
    minutes INTEGER NOT NULL,
    tiny INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    fire_at INTEGER,
    created_at INTEGER NOT NULL,
    updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sessions_due ON sessions(status, fire_at);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, status);
"""

# Статусы сессии:
#   proposed   — шаг предложен, ждём «Погнали»
#   running    — таймер идёт
#   awaiting   — таймер сработал, ждём ответ на чек-ин
#   step_done  — шаг сделан, ждём выбор «дальше / хватит»
#   closed     — закрыто (сделано, отложено или перезапуск)
ALLOWED_FIELDS = {"step_idx", "step_text", "minutes", "tiny", "status", "fire_at"}


class DB:
    def __init__(self, path: str):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        parent = os.path.dirname(self.path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.executescript(SCHEMA)
        await self.conn.commit()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def create_session(
        self, user_id: int, task_title: str, step_idx: int, step_text: str, minutes: int
    ) -> int:
        now = int(time.time())
        cur = await self.conn.execute(
            "INSERT INTO sessions (user_id, task_title, step_idx, step_text, minutes, tiny,"
            " status, fire_at, created_at, updated_at)"
            " VALUES (?, ?, ?, ?, ?, 0, 'proposed', NULL, ?, ?)",
            (user_id, task_title, step_idx, step_text, minutes, now, now),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_session(self, sid: int):
        cur = await self.conn.execute("SELECT * FROM sessions WHERE id = ?", (sid,))
        return await cur.fetchone()

    async def update_session(self, sid: int, **fields) -> None:
        bad = set(fields) - ALLOWED_FIELDS
        if bad:
            raise ValueError(f"Unknown fields: {bad}")
        fields["updated_at"] = int(time.time())
        cols = ", ".join(f"{k} = ?" for k in fields)
        await self.conn.execute(
            f"UPDATE sessions SET {cols} WHERE id = ?", (*fields.values(), sid)
        )
        await self.conn.commit()

    async def due_sessions(self, now: int):
        cur = await self.conn.execute(
            "SELECT * FROM sessions WHERE status = 'running' AND fire_at <= ?", (now,)
        )
        return await cur.fetchall()

    async def cancel_active(self, user_id: int) -> int:
        cur = await self.conn.execute(
            "UPDATE sessions SET status = 'closed', updated_at = ?"
            " WHERE user_id = ? AND status != 'closed'",
            (int(time.time()), user_id),
        )
        await self.conn.commit()
        return cur.rowcount
