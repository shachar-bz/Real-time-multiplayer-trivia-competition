import asyncio
import random

import pytest

from tests.fakes import FakeClock, RecordingEvents, eventually, make_question
from trivia.domain.bots import DifficultyProfile
from trivia.domain.match import Match
from trivia.domain.players import Player
from trivia.services.matchmaking import ALREADY_IN_GAME, NAME_REQUIRED, Matchmaker
from trivia.services.registry import GameRegistry


class Lobby:
    def __init__(self, countdown_seconds: int):
        self.events = RecordingEvents()
        self.registry = GameRegistry()
        self.clock = FakeClock()
        self.lineups: list[list[Player]] = []
        self.matchmaker = Matchmaker(
            events=self.events,
            registry=self.registry,
            start_match=self.start_match,
            countdown_seconds=countdown_seconds,
            clock=self.clock,
            rng=random.Random(3),
            bot_profiles=(DifficultyProfile("test", 1.0, 0, 0),),
        )

    async def start_match(self, lineup):
        self.lineups.append(lineup)


@pytest.fixture
async def lobby():
    lobby = Lobby(countdown_seconds=1)
    yield lobby
    await lobby.matchmaker.shutdown()


async def test_a_name_is_required(lobby):
    await lobby.matchmaker.join("sid-a", "   ", None, None)
    assert lobby.events.of("error") == [("sid-a", NAME_REQUIRED)]
    assert lobby.matchmaker.waiting_count == 0


async def test_players_already_in_a_match_cannot_queue(lobby):
    lobby.registry.add(
        Match("m", [Player.human("sid-a", "Alice")], [make_question()], question_seconds=20,
              clock=lobby.clock)
    )  # fmt: skip
    await lobby.matchmaker.join("sid-a", "Alice", None, None)
    assert lobby.events.of("error") == [("sid-a", ALREADY_IN_GAME)]


async def test_everyone_still_waiting_when_the_countdown_ends_races_together(lobby):
    await lobby.matchmaker.join("sid-a", "  Alice  ", "sportsCar", "blue")
    await lobby.matchmaker.join("sid-b", "Bob", None, None)
    await lobby.matchmaker.join("sid-c", "Carol", None, None)
    await lobby.matchmaker.leave("sid-b")

    await eventually(lambda: lobby.lineups)
    (lineup,) = lobby.lineups
    assert [player.id for player in lineup] == ["sid-a", "sid-c"]
    assert (lineup[0].name, lineup[0].ride, lineup[0].paint) == ("Alice", "sports_car", "blue")
    assert (["sid-a", "sid-b", "sid-c"], 1) in lobby.events.of("lobby_updated")
    assert lobby.events.of("lobby_updated")[-1] == (["sid-a", "sid-c"], 1)
    assert lobby.matchmaker.waiting_count == 0


async def test_status_counts_down_from_the_first_join():
    lobby = Lobby(countdown_seconds=30)
    await lobby.matchmaker.join("sid-a", "Alice", None, None)
    lobby.clock.advance(12.5)
    await lobby.matchmaker.join("sid-b", "Bob", None, None)
    assert lobby.events.of("lobby_updated")[-1] == (["sid-a", "sid-b"], 18)
    await lobby.matchmaker.shutdown()


async def test_a_lone_player_gets_bots():
    lobby = Lobby(countdown_seconds=0)
    await lobby.matchmaker.join("sid-a", "Alice", None, None)
    await eventually(lambda: lobby.lineups)

    human, *bots = lobby.lineups[0]
    assert human.id == "sid-a" and not human.is_bot
    assert 1 <= len(bots) <= 3 and all(bot.is_bot for bot in bots)


async def test_when_the_queue_empties_the_countdown_stops(lobby):
    await lobby.matchmaker.join("sid-a", "Alice", None, None)
    await lobby.matchmaker.leave("sid-a")
    await lobby.matchmaker.leave("sid-a")  # leaving twice is harmless
    await asyncio.sleep(1.2)
    assert lobby.lineups == []

    await lobby.matchmaker.join("sid-b", "Bob", None, None)  # a new countdown starts
    await eventually(lambda: lobby.lineups)
    assert lobby.lineups[0][0].id == "sid-b"
