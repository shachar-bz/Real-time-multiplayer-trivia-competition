import re

import pytest

from trivia.adapters.sqlite_chat import SqliteChatStore


@pytest.fixture
def store(tmp_path):
    return SqliteChatStore(tmp_path / "data" / "chat.db")


async def test_saved_messages_come_back_in_order_with_a_short_timestamp(store):
    first = await store.save_message("game-1", "sid-a", "Alice", "hi")
    second = await store.save_message("game-1", "sid-b", "Bob", "hello")
    await store.save_message("game-2", "sid-c", "Carol", "elsewhere")

    assert (first.game_id, first.user_id, first.username, first.content) == (
        "game-1", "sid-a", "Alice", "hi",
    )  # fmt: skip
    assert re.fullmatch(r"\d\d:\d\d", first.timestamp)
    assert await store.history("game-1") == [first, second]


async def test_unread_counters_grow_per_user_and_clear(store):
    assert await store.add_unread("game-1", ["sid-b", "sid-c"]) == {"sid-b": 1, "sid-c": 1}
    assert await store.add_unread("game-1", ["sid-b"]) == {"sid-b": 2}
    await store.clear_unread("game-1", "sid-b")
    assert await store.add_unread("game-1", ["sid-b", "sid-c"]) == {"sid-b": 1, "sid-c": 2}
    assert await store.add_unread("game-1", []) == {}


async def test_deleting_a_game_only_forgets_that_game(store):
    await store.save_message("game-1", "sid-a", "Alice", "bye")
    kept = await store.save_message("game-2", "sid-a", "Alice", "still here")
    await store.add_unread("game-1", ["sid-b"])

    await store.delete_game("game-1")

    assert await store.history("game-1") == []
    assert await store.history("game-2") == [kept]
    assert await store.add_unread("game-1", ["sid-b"]) == {"sid-b": 1}


def test_schema_creation_is_idempotent(tmp_path):
    SqliteChatStore(tmp_path / "chat.db")
    SqliteChatStore(tmp_path / "chat.db")
