import pytest

from tests.fakes import FakeClock, RecordingEvents, make_question
from trivia.adapters.sqlite_chat import SqliteChatStore
from trivia.domain.bots import BotBrain, DifficultyProfile
from trivia.domain.chat import MAX_MESSAGE_LENGTH
from trivia.domain.match import Match
from trivia.domain.players import Player
from trivia.services.chat_service import ChatService
from trivia.services.registry import GameRegistry


class Chat:
    def __init__(self, tmp_path):
        self.events = RecordingEvents()
        self.registry = GameRegistry()
        self.store = SqliteChatStore(tmp_path / "chat.db")
        self.service = ChatService(store=self.store, registry=self.registry, events=self.events)
        robot = Player.bot("bot-1", "Robo 🤖", "superbike", "blue",
                           BotBrain(DifficultyProfile("test", 1.0, 0, 0)))  # fmt: skip
        players = [Player.human("alice", "Alice"), Player.human("bob", "Bob"), robot]
        self.match = Match("game-1", players, [make_question()], question_seconds=20,
                           clock=FakeClock())  # fmt: skip
        self.registry.add(self.match)


@pytest.fixture
def chat(tmp_path):
    return Chat(tmp_path)


async def test_a_message_reaches_the_match_and_counts_as_unread_for_other_humans(chat):
    await chat.service.send_message("alice", "game-1", "hello racers")

    ((message, unread_counts),) = chat.events.of("chat_message_posted")
    assert (message.username, message.content, message.game_id) == ("Alice", "hello racers",
                                                                      "game-1")  # fmt: skip
    assert unread_counts == {"bob": 1}


@pytest.mark.parametrize(
    ("player_id", "game_id", "content"),
    [("stranger", "game-1", "hi"), ("alice", "no-such-game", "hi"), ("alice", "game-1", None),
     ("alice", ["not", "an", "id"], "hi")],
    ids=["not a player", "unknown game", "no content", "malformed game id"],
)  # fmt: skip
async def test_messages_outside_a_match_are_ignored(chat, player_id, game_id, content):
    await chat.service.send_message(player_id, game_id, content)
    assert chat.events.calls == []


@pytest.mark.parametrize(
    "content",
    ["", "   \n ", 42, ["hi"], {"text": "hi"}, "x" * (MAX_MESSAGE_LENGTH + 1)],
    ids=["empty", "whitespace", "number", "list", "object", "too long"],
)
async def test_only_non_empty_text_within_the_limit_is_posted(chat, content):
    await chat.service.send_message("alice", "game-1", content)
    assert chat.events.calls == []
    assert await chat.store.history("game-1") == []


async def test_messages_are_posted_without_surrounding_whitespace(chat):
    await chat.service.send_message("alice", "game-1", "  hello racers \n")
    await chat.service.send_message("alice", "game-1", "x" * MAX_MESSAGE_LENGTH)

    posted = [message.content for message, _ in chat.events.of("chat_message_posted")]
    assert posted == ["hello racers", "x" * MAX_MESSAGE_LENGTH]


async def test_only_players_of_the_match_can_read_its_chat(chat):
    await chat.service.send_message("alice", "game-1", "our secret plan")
    chat.events.calls.clear()

    await chat.service.send_history("stranger", "game-1")
    await chat.service.open_chat("stranger", "game-1")
    await chat.service.send_history("alice", "no-such-game")
    await chat.service.open_chat("alice", ["not", "an", "id"])

    assert chat.events.calls == []
    assert (await chat.store.add_unread("game-1", ["bob"])) == {"bob": 2}  # untouched


async def test_opening_the_chat_clears_unread_messages(chat):
    await chat.service.send_message("alice", "game-1", "one")
    await chat.service.open_chat("bob", "game-1")
    await chat.service.send_message("alice", "game-1", "two")

    assert chat.events.of("chat_unread_changed") == [("bob", 0)]
    assert chat.events.of("chat_message_posted")[-1][1] == {"bob": 1}


async def test_history_is_sent_to_the_requesting_player(chat):
    await chat.service.send_message("alice", "game-1", "one")
    await chat.service.send_message("bob", "game-1", "two")
    await chat.service.send_history("bob", "game-1")

    ((player_id, messages),) = chat.events.of("chat_history")
    assert player_id == "bob"
    assert [message.content for message in messages] == ["one", "two"]


async def test_closing_the_chat_clears_it_for_players_and_storage(chat):
    await chat.service.send_message("alice", "game-1", "bye")
    await chat.service.close_chat(chat.match)

    assert chat.events.of("chat_cleared") == [("game-1",)]
    assert await chat.store.history("game-1") == []
