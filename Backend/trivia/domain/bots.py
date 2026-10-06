"""Computer opponents that keep a solo player company.

A bot is a regular `Player` with a `BotBrain`. Each round the brain plans how
long to "think" and which option to pick, based on its difficulty profile.
"""

import random
import uuid
from dataclasses import dataclass

from trivia.domain.players import Player
from trivia.domain.questions import Question
from trivia.domain.vehicles import PAINTS, RIDES


@dataclass(frozen=True)
class DifficultyProfile:
    name: str
    accuracy: float  # chance of picking the correct option
    min_delay_seconds: float
    max_delay_seconds: float


EASY = DifficultyProfile("easy", accuracy=0.40, min_delay_seconds=2, max_delay_seconds=8)
MEDIUM = DifficultyProfile("medium", accuracy=0.65, min_delay_seconds=5, max_delay_seconds=13)
HARD = DifficultyProfile("hard", accuracy=0.85, min_delay_seconds=10, max_delay_seconds=18)
DEFAULT_PROFILES = (EASY, MEDIUM, HARD)

MIN_BOTS_PER_SOLO_GAME = 1
MAX_BOTS_PER_SOLO_GAME = 3
BOT_NAME_SUFFIX = " 🤖"
BOT_NAMES = (
    "Nova", "Zippy", "Pixel", "Blaze", "Echo", "Quark", "Luna", "Milo", "Kira",
    "Atlas", "Juno", "Rafi", "Sage", "Nico", "Vega", "Skye", "Orion", "Mika",
)  # fmt: skip


@dataclass(frozen=True)
class BotPlan:
    delay_seconds: float
    option: str


@dataclass(frozen=True)
class BotBrain:
    profile: DifficultyProfile

    def plan(self, question: Question, rng: random.Random) -> BotPlan:
        delay = rng.uniform(self.profile.min_delay_seconds, self.profile.max_delay_seconds)
        if rng.random() < self.profile.accuracy:
            option = question.correct_option
        else:
            option = rng.choice(question.wrong_options)
        return BotPlan(delay_seconds=delay, option=option)


def create_bots(
    rng: random.Random,
    profiles: tuple[DifficultyProfile, ...] = DEFAULT_PROFILES,
) -> list[Player]:
    """1-3 bots with distinct names, random vehicles and random difficulty."""
    count = rng.randint(MIN_BOTS_PER_SOLO_GAME, MAX_BOTS_PER_SOLO_GAME)
    return [
        Player.bot(
            player_id=str(uuid.UUID(int=rng.getrandbits(128), version=4)),
            name=name + BOT_NAME_SUFFIX,
            ride=rng.choice(list(RIDES)),
            paint=rng.choice(list(PAINTS)),
            brain=BotBrain(rng.choice(profiles)),
        )
        for name in rng.sample(BOT_NAMES, count)
    ]
