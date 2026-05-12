import sqlite3

from chat_db import CHAT_DB_PATH, init_chat_db
from sound_events import SOUND_CHAT_MESSAGE, emit_sound_to_room


def _connect():
    init_chat_db()
    connection = sqlite3.connect(CHAT_DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _format_message(row):
    return {
        "id": row["id"],
        "game_id": row["game_id"],
        "user_id": row["user_id"],
        "username": row["username"],
        "content": row["content"],
        "timestamp": row["timestamp"],
    }


def save_message(game_id, user_id, username, content):
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (game_id, user_id, username, content)
            VALUES (?, ?, ?, ?)
            """,
            (game_id, user_id, username, content),
        )
        row = connection.execute(
            """
            SELECT id, game_id, user_id, username, content, strftime('%H:%M', timestamp) AS timestamp
            FROM messages
            WHERE id = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()

    return _format_message(row)


def get_history(game_id, requesting_user_id):
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, user_id, username, content, strftime('%H:%M', timestamp) AS timestamp
            FROM messages
            WHERE game_id = ?
            ORDER BY messages.timestamp ASC, id ASC
            """,
            (game_id,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "username": row["username"],
            "content": row["content"],
            "timestamp": row["timestamp"],
            "is_own": row["user_id"] == requesting_user_id,
        }
        for row in rows
    ]


async def delete_game_chat(game_id):
    with _connect() as connection:
        connection.execute(
            """
            DELETE FROM messages
            WHERE game_id = ?
            """,
            (game_id,),
        )
        connection.execute(
            """
            DELETE FROM unread_counts
            WHERE game_id = ?
            """,
            (game_id,),
        )


def increment_unread_for_others(game_id, sender_user_id, all_player_ids):
    unread_rows = [
        (game_id, player_id)
        for player_id in all_player_ids
        if player_id != sender_user_id
    ]

    if not unread_rows:
        return

    with _connect() as connection:
        connection.executemany(
            """
            INSERT INTO unread_counts (game_id, user_id, unread_count)
            VALUES (?, ?, 1)
            ON CONFLICT(game_id, user_id) DO UPDATE SET
                unread_count = unread_count + 1
            """,
            unread_rows,
        )


def reset_unread(game_id, user_id):
    with _connect() as connection:
        connection.execute(
            """
            UPDATE unread_counts
            SET unread_count = 0
            WHERE game_id = ? AND user_id = ?
            """,
            (game_id, user_id),
        )


def get_unread_count(game_id, user_id):
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT unread_count
            FROM unread_counts
            WHERE game_id = ? AND user_id = ?
            """,
            (game_id, user_id),
        ).fetchone()

    if row is None:
        return 0

    return row["unread_count"]


def register_chat_handlers(sio, games):
    @sio.on("chat_send_message")
    async def chat_send_message(sid, payload):
        payload = payload or {}
        game_id = payload.get("game_id")
        content = payload.get("content")
        game = games.get(game_id)

        if game is None or sid not in game["players"] or content is None:
            return

        username = game["players"][sid]["name"]
        message = save_message(game_id, sid, username, content)
        await sio.emit("chat_new_message", message, room=game_id)

        other_sids = [
            player_sid
            for player_sid in game["players"]
            if player_sid != sid
        ]
        increment_unread_for_others(game_id, sid, other_sids)

        for other_sid in other_sids:
            unread_count = get_unread_count(game_id, other_sid)
            await sio.emit(
                "chat_unread_update",
                {"unread_count": unread_count},
                to=other_sid,
            )

        await emit_sound_to_room(sio, game_id, SOUND_CHAT_MESSAGE, skip_sid=sid)

    @sio.on("chat_open")
    async def chat_open(sid, payload):
        payload = payload or {}
        game_id = payload.get("game_id")

        reset_unread(game_id, sid)
        await sio.emit("chat_unread_update", {"unread_count": 0}, to=sid)

    @sio.on("chat_request_history")
    async def chat_request_history(sid, payload):
        payload = payload or {}
        game_id = payload.get("game_id")
        history = get_history(game_id, sid)

        await sio.emit("chat_history", history, to=sid)
