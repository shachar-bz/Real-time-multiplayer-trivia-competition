"""Chat messages and unread counters, stored in SQLite for the lifetime of a game."""

import asyncio
import sqlite3
from contextlib import closing
from pathlib import Path

from trivia.domain.chat import ChatMessage

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    username TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS unread_counts (
    game_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    unread_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (game_id, user_id)
);
"""

# Timestamps are stored in UTC and shown as "HH:MM".
SELECT_MESSAGES_SQL = """
SELECT id, game_id, user_id, username, content, strftime('%H:%M', timestamp) AS timestamp
FROM messages
"""


class SqliteChatStore:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as connection:
            connection.executescript(SCHEMA_SQL)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    async def save_message(
        self, game_id: str, user_id: str, username: str, content: str
    ) -> ChatMessage:
        return await asyncio.to_thread(self._save_message, game_id, user_id, username, content)

    async def history(self, game_id: str) -> list[ChatMessage]:
        return await asyncio.to_thread(self._history, game_id)

    async def add_unread(self, game_id: str, user_ids: list[str]) -> dict[str, int]:
        return await asyncio.to_thread(self._add_unread, game_id, user_ids)

    async def clear_unread(self, game_id: str, user_id: str) -> None:
        await asyncio.to_thread(self._clear_unread, game_id, user_id)

    async def delete_game(self, game_id: str) -> None:
        await asyncio.to_thread(self._delete_game, game_id)

    def _save_message(self, game_id, user_id, username, content) -> ChatMessage:
        with closing(self._connect()) as connection, connection:
            cursor = connection.execute(
                "INSERT INTO messages (game_id, user_id, username, content) VALUES (?, ?, ?, ?)",
                (game_id, user_id, username, content),
            )
            row = connection.execute(
                SELECT_MESSAGES_SQL + "WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()
        return message_from_row(row)

    def _history(self, game_id) -> list[ChatMessage]:
        with closing(self._connect()) as connection:
            rows = connection.execute(
                SELECT_MESSAGES_SQL + "WHERE game_id = ? ORDER BY messages.timestamp ASC, id ASC",
                (game_id,),
            ).fetchall()
        return [message_from_row(row) for row in rows]

    def _add_unread(self, game_id, user_ids) -> dict[str, int]:
        if not user_ids:
            return {}
        with closing(self._connect()) as connection, connection:
            connection.executemany(
                """
                INSERT INTO unread_counts (game_id, user_id, unread_count) VALUES (?, ?, 1)
                ON CONFLICT(game_id, user_id) DO UPDATE SET unread_count = unread_count + 1
                """,
                [(game_id, user_id) for user_id in user_ids],
            )
            return {
                user_id: connection.execute(
                    "SELECT unread_count FROM unread_counts WHERE game_id = ? AND user_id = ?",
                    (game_id, user_id),
                ).fetchone()["unread_count"]
                for user_id in user_ids
            }

    def _clear_unread(self, game_id, user_id) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                "UPDATE unread_counts SET unread_count = 0 WHERE game_id = ? AND user_id = ?",
                (game_id, user_id),
            )

    def _delete_game(self, game_id) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute("DELETE FROM messages WHERE game_id = ?", (game_id,))
            connection.execute("DELETE FROM unread_counts WHERE game_id = ?", (game_id,))


def message_from_row(row: sqlite3.Row) -> ChatMessage:
    return ChatMessage(
        id=row["id"],
        game_id=row["game_id"],
        user_id=row["user_id"],
        username=row["username"],
        content=row["content"],
        timestamp=row["timestamp"],
    )
