"""Test doubles shared by the unit tests."""

from trivia.domain.questions import Question


class FakeClock:
    """A clock that only moves when a test says so."""

    def __init__(self, now: float = 1000.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def make_question(question_id: int = 1, correct_option: str = "C") -> Question:
    return Question(
        id=question_id,
        topic="Science",
        difficulty=3,
        text=f"Question number {question_id}?",
        options={key: f"Answer {key}" for key in "ABCD"},
        correct_option=correct_option,
    )
