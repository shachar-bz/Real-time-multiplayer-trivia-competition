"""The three one-time helps ("lifelines") every human player starts with."""

import random
from enum import StrEnum

from trivia.domain.questions import Question

FIFTY_FIFTY_REMOVED_OPTIONS = 2


class Lifeline(StrEnum):
    FIFTY_FIFTY = "fifty_fifty"
    DOUBLE_SCORE = "double_score"
    CALL_A_FRIEND = "call_a_friend"

    @classmethod
    def parse(cls, value: object) -> "Lifeline | None":
        try:
            return cls(str(value))
        except ValueError:
            return None


def options_to_remove(question: Question, rng: random.Random) -> list[str]:
    """Fifty-fifty: remove two of the three wrong options at random."""
    return rng.sample(question.wrong_options, FIFTY_FIFTY_REMOVED_OPTIONS)
