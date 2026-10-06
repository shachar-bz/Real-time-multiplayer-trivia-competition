import asyncio
import random
import time

import pytest

from tests.fakes import FakeFriendAdvisor, FakeQuestionBank, RecordingEvents, eventually
from tests.fakes import make_question
from trivia.adapters.sqlite_chat import SqliteChatStore
from trivia.domain.bots import BotBrain, DifficultyProfile
from trivia.domain.lifelines import Lifeline
from trivia.domain.match import LIFELINE_ALREADY_USED
from trivia.domain.players import Player
from trivia.services.chat_service import ChatService
from trivia.services.game_service import (
    FRIEND_NOT_ANSWERING,
    MATCH_COULD_NOT_START,
    GameService,
)
from trivia.services.registry import GameRegistry


class Game:
    """A GameService wired to fakes, plus helpers to drive one match."""

    def __init__(
        self, tmp_path, *, question_seconds=5.0, friend=None, friend_timeout=1.0, questions=None
    ):
        self.events = RecordingEvents()
        self.registry = GameRegistry()
        self.friend = friend or FakeFriendAdvisor()
        chat = ChatService(
            store=SqliteChatStore(tmp_path / "chat.db"), registry=self.registry, events=self.events
        )
        self.service = GameService(
            events=self.events,
            registry=self.registry,
            question_bank=FakeQuestionBank(
                questions or [make_question(1, "C"), make_question(2, "A")]
            ),
            friend_advisor=self.friend,
            chat=chat,
            question_seconds=question_seconds,
            questions_per_game=2,
            result_seconds=0.01,
            friend_timeout_seconds=friend_timeout,
            friend_confidence_range=(30, 100),
            clock=time.monotonic,
            rng=random.Random(0),
        )
        self.match = None

    async def start(self, *players):
        await self.service.start_match(list(players))
        self.match = self.registry.match_for_player(players[0].id)
        await self.question(1)

    async def question(self, number):
        await eventually(lambda: len(self.events.of("question_started")) >= number)

    async def rounds_finished(self, count):
        await eventually(lambda: len(self.events.of("round_finished")) >= count)

    async def closed(self):
        await eventually(lambda: self.events.of("match_closed"))


def alice():
    return Player.human("alice", "Alice")


def bob():
    return Player.human("bob", "Bob")


def bot(delay_seconds):
    profile = DifficultyProfile("test", accuracy=1.0, min_delay_seconds=delay_seconds,
                                max_delay_seconds=delay_seconds)  # fmt: skip
    return Player.bot("bot-1", "Robo 🤖", "superbike", "blue", BotBrain(profile))


@pytest.fixture
async def game(tmp_path):
    game = Game(tmp_path)
    yield game
    await game.service.shutdown()


async def test_a_match_plays_every_question_and_then_cleans_up(game):
    await game.start(alice(), bob())
    assert game.registry.is_playing("alice")

    await game.service.submit_answer("alice", 1, "C")
    await game.service.submit_answer("bob", 1, "B")
    await game.question(2)
    await game.service.submit_answer("alice", 2, "A")
    await game.service.submit_answer("bob", 2, "A")
    await game.closed()

    assert game.events.names() == [
        "match_started",
        "question_started",
        "answer_accepted", "standings_changed",
        "answer_accepted", "standings_changed",
        "round_finished",
        "question_started",
        "answer_accepted", "standings_changed",
        "answer_accepted", "standings_changed",
        "round_finished",
        "match_finished",
        "chat_cleared",
        "match_closed",
    ]  # fmt: skip
    assert len(game.registry) == 0 and not game.registry.is_playing("alice")
    assert game.match.players["alice"].score > game.match.players["bob"].score > 0


async def test_players_are_told_when_their_match_cannot_start(tmp_path):
    game = Game(tmp_path, questions=[make_question(1)])  # a match needs two
    await game.service.start_match([alice(), bot(delay_seconds=0.01), bob()])

    assert game.events.calls == [
        ("error", "alice", MATCH_COULD_NOT_START),
        ("error", "bob", MATCH_COULD_NOT_START),
    ]
    assert len(game.registry) == 0 and not game.registry.is_playing("alice")


async def test_a_round_waits_for_the_timer_when_someone_does_not_answer(tmp_path):
    game = Game(tmp_path, question_seconds=0.3)
    await game.start(alice(), bob())
    started = time.monotonic()
    await game.service.submit_answer("alice", 1, "C")
    await game.rounds_finished(1)

    assert time.monotonic() - started >= 0.25
    alice_result, bob_result = game.events.of("round_finished")[0][0]
    assert (alice_result.selected_option, bob_result.selected_option) == ("C", None)
    await game.service.shutdown()


async def test_disconnected_players_are_not_waited_for(game):
    await game.start(alice(), bob())
    await game.service.submit_answer("alice", 1, "C")
    await game.service.player_disconnected("bob")
    await game.rounds_finished(1)  # long before the 5 second timer

    assert not game.match.players["bob"].connected
    names = game.events.names()
    assert names[names.index("round_finished") - 1] == "standings_changed"  # Bob left


async def test_bots_answer_through_the_same_rules_without_answer_feedback(game):
    await game.start(alice(), bot(delay_seconds=0.01))
    await eventually(lambda: game.match.players["bot-1"].score > 0)
    await game.service.submit_answer("alice", 1, "C")
    await game.rounds_finished(1)

    accepted = [outcome.player.id for (outcome,) in game.events.of("answer_accepted")]
    assert accepted == ["alice"]
    assert game.events.names()[:3] == ["match_started", "question_started", "standings_changed"]


async def test_slow_bots_are_stopped_when_their_round_ends(tmp_path):
    game = Game(tmp_path, question_seconds=0.2)
    await game.start(alice(), bot(delay_seconds=0.3))
    await game.service.submit_answer("alice", 1, "C")
    await game.closed()
    await asyncio.sleep(0.4)  # long enough for a leaked round-1 bot answer to land

    assert game.match.players["bot-1"].score == 0
    assert "standings_changed" not in game.events.names()[1:3]
    assert all(r.selected_option is None for (results,) in game.events.of("round_finished")
               for r in results if r.player.is_bot)  # fmt: skip


async def test_fifty_fifty_and_double_score_reach_only_the_player(game):
    await game.start(alice(), bob())
    await game.service.use_lifeline("alice", Lifeline.FIFTY_FIFTY, 1)
    await game.service.use_lifeline("alice", Lifeline.FIFTY_FIFTY, 1)
    await game.service.use_lifeline("bob", Lifeline.DOUBLE_SCORE, 1)

    (fifty,), (double,) = game.events.of("lifeline_used")
    assert fifty.player.id == "alice" and len(fifty.removed_options) == 2
    assert double.player.id == "bob" and double.lifeline is Lifeline.DOUBLE_SCORE
    assert game.events.of("error") == [("alice", LIFELINE_ALREADY_USED)]


async def test_calling_a_friend_pauses_the_round_until_the_friend_replies(tmp_path):
    game = Game(tmp_path, question_seconds=0.3, friend=FakeFriendAdvisor("Pick C", delay=0.5))
    await game.start(alice(), bob())
    await game.service.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1)

    assert game.events.names()[2:5] == ["timer_paused", "lifeline_used", "timer_resumed"]
    assert game.events.of("round_finished") == []  # 0.5s call > 0.3s timer, but it was paused
    (used,) = game.events.of("lifeline_used")[0]
    assert used.friend_reply.message == "Pick C" and used.friend_reply.answered
    assert 30 <= used.friend_reply.confidence <= 100
    assert game.friend.calls == [(1, used.friend_reply.confidence)]
    await game.rounds_finished(1)
    await game.service.shutdown()


async def test_a_friend_who_takes_too_long_is_not_answering(tmp_path):
    game = Game(tmp_path, friend=FakeFriendAdvisor(delay=1.0), friend_timeout=0.05)
    await game.start(alice(), bob())
    await game.service.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1)

    (used,) = game.events.of("lifeline_used")[0]
    assert (used.friend_reply.message, used.friend_reply.answered) == (FRIEND_NOT_ANSWERING, False)
    assert game.events.names()[-1] == "timer_resumed"
    await game.service.shutdown()


async def test_a_failed_friend_call_is_refunded_and_reported(tmp_path):
    failing = FakeFriendAdvisor(error=RuntimeError("Missing OPENAI_API_KEY in .env file."))
    game = Game(tmp_path, friend=failing)
    await game.start(alice(), bob())
    await game.service.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1)

    assert game.events.names()[2:] == ["timer_paused", "timer_resumed", "error"]
    assert game.events.of("error") == [("alice", "Missing OPENAI_API_KEY in .env file.")]
    assert game.match.players["alice"].has_lifeline(Lifeline.CALL_A_FRIEND)
    await game.service.shutdown()


async def test_a_friend_call_that_outlives_its_round_leaves_the_next_round_alone(tmp_path):
    game = Game(tmp_path, friend=FakeFriendAdvisor(delay=0.3))
    await game.start(alice(), bob())
    call = asyncio.create_task(game.service.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1))
    await eventually(lambda: game.events.of("timer_paused"))
    await game.service.submit_answer("alice", 1, "C")
    await game.service.submit_answer("bob", 1, "C")
    await game.question(2)
    await call

    assert game.events.of("lifeline_used")  # the caller still hears the friend
    assert game.events.of("timer_resumed") == []
    assert not game.match.round.timer.paused
    await game.service.shutdown()


async def test_requests_from_players_outside_a_match_are_ignored(game):
    await game.service.submit_answer("nobody", 1, "C")
    await game.service.use_lifeline("nobody", Lifeline.FIFTY_FIFTY, 1)
    await game.service.player_disconnected("nobody")
    assert game.events.calls == []
