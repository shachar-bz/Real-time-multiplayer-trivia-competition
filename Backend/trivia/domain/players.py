"""Players: humans (identified by their Socket.IO session id) and bots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from trivia.domain.lifelines import Lifeline
from trivia.domain.vehicles import DEFAULT_PAINT, DEFAULT_RIDE, normalize_paint, normalize_ride

if TYPE_CHECKING:
    from trivia.domain.bots import BotBrain

MAX_NAME_LENGTH = 24


def clean_player_name(raw_name: object) -> str:
    """Trim and shorten a requested name. An empty result means "no name"."""
    return str(raw_name).strip()[:MAX_NAME_LENGTH]


@dataclass(eq=False)
class Player:
    id: str
    name: str
    ride: str = DEFAULT_RIDE
    paint: str = DEFAULT_PAINT
    brain: BotBrain | None = None  # set for bots only
    lifelines: set[Lifeline] = field(default_factory=set)
    score: int = 0
    connected: bool = True

    @classmethod
    def human(cls, player_id: str, name: str, ride: object = None, paint: object = None) -> Player:
        """A human starts with every lifeline; unknown vehicles fall back to defaults."""
        return cls(
            id=player_id,
            name=name,
            ride=normalize_ride(ride),
            paint=normalize_paint(paint),
            lifelines=set(Lifeline),
        )

    @classmethod
    def bot(cls, player_id: str, name: str, ride: str, paint: str, brain: BotBrain) -> Player:
        """Bots never use lifelines."""
        return cls(id=player_id, name=name, ride=ride, paint=paint, brain=brain)

    @property
    def is_bot(self) -> bool:
        return self.brain is not None

    def has_lifeline(self, lifeline: Lifeline) -> bool:
        return lifeline in self.lifelines
