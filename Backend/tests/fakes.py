"""Test doubles shared by the unit tests."""

import asyncio

from trivia.domain.questions import Question
from trivia.services.ports import NotEnoughQuestionsError


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


class FakeQuestionBank:
    """Hands out the given questions in order.

    Clear `ready` to keep `draw` waiting, e.g. to act while a match is being set up.
    """

    def __init__(self, questions: list[Question]):
        self.questions = questions
        self.ready = asyncio.Event()
        self.ready.set()

    async def draw(self, count: int) -> list[Question]:
        await self.ready.wait()
        if len(self.questions) < count:
            raise NotEnoughQuestionsError(f"Expected at least {count} questions.")
        return self.questions[:count]


class FakeFriendAdvisor:
    """Replies after `delay` seconds, or raises `error` if one is given."""

    def __init__(self, reply: str = "Go with C!", delay: float = 0.0, error: Exception = None):
        self.reply = reply
        self.delay = delay
        self.error = error
        self.calls: list[tuple[int, int]] = []  # (question id, confidence)

    async def advise(self, question: Question, confidence: int) -> str:
        self.calls.append((question.id, confidence))
        await asyncio.sleep(self.delay)
        if self.error is not None:
            raise self.error
        return self.reply


class RecordingEvents:
    """A GameEvents port that records every call as (event name, arguments...)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []

    def names(self) -> list[str]:
        return [call[0] for call in self.calls]

    def of(self, name: str) -> list[tuple]:
        """The arguments of every call to `name`, oldest first."""
        return [call[1:] for call in self.calls if call[0] == name]

    async def lobby_updated(self, waiting, seconds_left):
        self.calls.append(("lobby_updated", [player.id for player in waiting], seconds_left))

    async def error(self, player_id, message):
        self.calls.append(("error", player_id, message))

    async def match_started(self, match):
        self.calls.append(("match_started", match))

    async def question_started(self, match):
        self.calls.append(("question_started", match.round.question.id))

    async def answer_accepted(self, match, outcome):
        self.calls.append(("answer_accepted", outcome))

    async def standings_changed(self, match):
        self.calls.append(("standings_changed", {p.id: p.score for p in match.players.values()}))

    async def lifeline_used(self, used):
        self.calls.append(("lifeline_used", used))

    async def timer_paused(self, match, caller):
        self.calls.append(("timer_paused", caller.id, match.round.timer.seconds_left()))

    async def timer_resumed(self, match):
        self.calls.append(("timer_resumed", match.round.question.id))

    async def round_finished(self, match):
        self.calls.append(("round_finished", match.round_results()))

    async def match_finished(self, match):
        self.calls.append(("match_finished", match))

    async def match_closed(self, match):
        self.calls.append(("match_closed", match.id))

    async def chat_message_posted(self, match, message, unread_counts):
        self.calls.append(("chat_message_posted", message, unread_counts))

    async def chat_unread_changed(self, player_id, count):
        self.calls.append(("chat_unread_changed", player_id, count))

    async def chat_history(self, player_id, messages):
        self.calls.append(("chat_history", player_id, messages))

    async def chat_cleared(self, match):
        self.calls.append(("chat_cleared", match.id))


async def eventually(condition, timeout: float = 3.0):
    """Wait until `condition()` is truthy, or fail the test after `timeout` seconds."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not condition():
        if loop.time() > deadline:
            raise AssertionError("condition was not met in time")
        await asyncio.sleep(0.005)
