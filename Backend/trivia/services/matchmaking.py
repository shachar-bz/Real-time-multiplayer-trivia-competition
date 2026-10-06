"""The lobby: players queue up, a countdown runs, and everyone waiting races together.

The first player to join starts a countdown. Every second (and whenever the
queue changes) each waiting player gets the lobby status. When the countdown
ends, the whole queue becomes one match; a player who is alone gets bots.
"""

import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

from trivia.domain.bots import DEFAULT_PROFILES, DifficultyProfile, create_bots
from trivia.domain.players import Player, clean_player_name
from trivia.domain.timer import Clock
from trivia.services.ports import GameEvents
from trivia.services.registry import GameRegistry

logger = logging.getLogger(__name__)

ALREADY_IN_GAME = "You are already in a game."
NAME_REQUIRED = "Username is required to start the game."
COUNTDOWN_TICK_SECONDS = 1

StartMatch = Callable[[list[Player]], Awaitable[None]]


class Matchmaker:
    def __init__(
        self,
        *,
        events: GameEvents,
        registry: GameRegistry,
        start_match: StartMatch,
        countdown_seconds: int,
        clock: Clock,
        rng: random.Random,
        bot_profiles: tuple[DifficultyProfile, ...] = DEFAULT_PROFILES,
    ):
        self._events = events
        self._registry = registry
        self._start_match = start_match
        self._countdown_seconds = countdown_seconds
        self._clock = clock
        self._rng = rng
        self._bot_profiles = bot_profiles
        self._waiting: dict[str, Player] = {}  # in joining order
        self._countdown: asyncio.Task | None = None
        self._countdown_started_at: float | None = None

    @property
    def waiting_count(self) -> int:
        return len(self._waiting)

    async def join(self, player_id: str, name: object, ride: object, paint: object) -> None:
        if self._registry.is_playing(player_id):
            await self._events.error(player_id, ALREADY_IN_GAME)
            return

        player_name = clean_player_name(name)
        if not player_name:
            await self._events.error(player_id, NAME_REQUIRED)
            return

        self._waiting[player_id] = Player.human(player_id, player_name, ride, paint)
        if self._countdown is None:
            self._countdown_started_at = self._clock()
            self._countdown = asyncio.create_task(self._count_down())
        await self._broadcast_status()

    async def leave(self, player_id: str) -> None:
        if self._waiting.pop(player_id, None) is None:
            return

        if self._waiting:
            await self._broadcast_status()
        elif self._countdown is not None:
            self._countdown.cancel()
            self._countdown = None
            self._countdown_started_at = None

    async def shutdown(self) -> None:
        if self._countdown is not None:
            self._countdown.cancel()

    async def _count_down(self) -> None:
        try:
            for _ in range(self._countdown_seconds):
                await self._broadcast_status()
                await asyncio.sleep(COUNTDOWN_TICK_SECONDS)
            await self._broadcast_status()
        finally:
            if self._countdown is asyncio.current_task():
                self._countdown = None
                self._countdown_started_at = None

        lineup = list(self._waiting.values())
        self._waiting.clear()
        if len(lineup) == 1:
            lineup += create_bots(self._rng, self._bot_profiles)
        if lineup:
            try:
                await self._start_match(lineup)
            except Exception:
                logger.exception("Could not start a match for %s", [p.name for p in lineup])

    async def _broadcast_status(self) -> None:
        if not self._waiting:
            return

        started_at = self._countdown_started_at
        elapsed = 0 if started_at is None else self._clock() - started_at
        seconds_left = max(0, self._countdown_seconds - int(elapsed))
        await self._events.lobby_updated(list(self._waiting.values()), seconds_left)
