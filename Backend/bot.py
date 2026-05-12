import asyncio
import random
import time
import uuid

from helpers import points_for_answer
from player_profile import PAINT_CHOICES, RIDE_CHOICES


BOT_NAMES = [
    "Nova",
    "Zippy",
    "Pixel",
    "Blaze",
    "Echo",
    "Quark",
    "Luna",
    "Milo",
    "Kira",
    "Atlas",
    "Juno",
    "Rafi",
    "Sage",
    "Nico",
    "Vega",
    "Skye",
    "Orion",
    "Mika",
]

DIFFICULTY_SETTINGS = {
    "easy": {"accuracy": 0.40, "delay_min": 2, "delay_max": 8},
    "medium": {"accuracy": 0.65, "delay_min": 5, "delay_max": 13},
    "hard": {"accuracy": 0.85, "delay_min": 10, "delay_max": 18},
}


class Bot:
    def __init__(
        self,
        name: str,
        difficulty: str = "medium",
        ride: str = None,
        paint: str = None,
    ):
        self.sid = str(uuid.uuid4())
        self.name = name +  " 🤖"
        self.difficulty = difficulty
        self.is_bot = True
        self.ride = ride or random.choice(list(RIDE_CHOICES))
        self.paint = paint or random.choice(list(PAINT_CHOICES))

    def to_player_dict(self) -> dict:
        return {
            "sid": self.sid,
            "name": self.name,
            "ride": self.ride,
            "paint": self.paint,
            "score": 0,
            "connected": True,
            "is_bot": True,
            "helps": {
                "fifty_fifty": False,
                "double_score": False,
                "call_a_friend": False,
            },
        }

    async def answer(
        self,
        game: dict,
        correct_option: str,
        valid_options: set,
        on_score_change=None,
    ):
        settings = DIFFICULTY_SETTINGS[self.difficulty]
        delay = random.uniform(settings["delay_min"], settings["delay_max"])
        await asyncio.sleep(delay)

        if game["accepting_answers"] and self.sid not in game["answers"]:
            if random.random() < settings["accuracy"]:
                selected = correct_option
            else:
                wrong_options = list(valid_options - {correct_option})
                selected = random.choice(wrong_options)

            game["answers"][self.sid] = selected
            if game["question_timer_paused"]:
                remaining_time = game["timer_remaining_seconds"]
            else:
                remaining_time = max(0, game["question_deadline"] - time.monotonic())

            points_earned = points_for_answer(
                selected,
                correct_option,
                used_double_score=False,
                remaining_time=remaining_time,
                total_time=game["question_seconds"],
            )
            game["players"][self.sid]["score"] += points_earned
            game["answer_points"][self.sid] = points_earned
            if on_score_change is not None:
                await on_score_change(game)


class BotFactory:
    @staticmethod
    def create_bots_for_solo_game() -> list[Bot]:
        count = random.randint(1, 3)
        names = BOT_NAMES.copy()
        random.shuffle(names)

        return [
            Bot(name=name, difficulty=random.choice(["easy", "medium", "hard"]))
            for name in names[:count]
        ]
