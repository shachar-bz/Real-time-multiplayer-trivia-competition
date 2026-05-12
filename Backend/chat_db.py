import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CHAT_DB_PATH = BASE_DIR / "chat.db"


def init_chat_db():
    with sqlite3.connect(CHAT_DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                username TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS unread_counts (
                game_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                unread_count INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (game_id, user_id)
            )
            """
        )


init_chat_db()
