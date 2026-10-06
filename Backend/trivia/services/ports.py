"""Ports: everything the application services need from the outside world.

Services depend only on these Protocols. The SQLite and OpenAI adapters and
the Socket.IO publisher implement them; tests plug in in-memory fakes.
"""

from typing import Protocol

from trivia.domain.chat import ChatMessage
from trivia.domain.match import AnswerOutcome, LifelineUsed, Match
from trivia.domain.players import Player
from trivia.domain.questions import Question


class NotEnoughQuestionsError(RuntimeError):
    """The question bank cannot fill a game."""


class QuestionBank(Protocol):
    async def draw(self, count: int) -> list[Question]:
        """Return `count` random, distinct questions or raise NotEnoughQuestionsError."""
        ...


class ChatStore(Protocol):
    async def save_message(
        self, game_id: str, user_id: str, username: str, content: str
    ) -> ChatMessage: ...

    async def history(self, game_id: str) -> list[ChatMessage]:
        """Oldest message first."""
        ...

    async def add_unread(self, game_id: str, user_ids: list[str]) -> dict[str, int]:
        """Count one more unread message for each user; return their new unread counts."""
        ...

    async def clear_unread(self, game_id: str, user_id: str) -> None: ...

    async def delete_game(self, game_id: str) -> None:
        """Forget every message and unread counter of a finished game."""
        ...


class FriendAdvisor(Protocol):
    async def advise(self, question: Question, confidence: int) -> str:
        """What the friend on the phone says. `confidence` (0-100) sets the tone."""
        ...


class GameEvents(Protocol):
    """What happened, in game terms. The api layer turns these into Socket.IO events."""

    # Lobby
    async def lobby_updated(self, waiting: list[Player], seconds_left: int) -> None: ...

    async def error(self, player_id: str, message: str) -> None: ...

    # Match flow
    async def match_started(self, match: Match) -> None: ...

    async def question_started(self, match: Match) -> None: ...

    async def answer_accepted(self, match: Match, outcome: AnswerOutcome) -> None:
        """A human's answer counted. (Bots only trigger `standings_changed`.)"""
        ...

    async def standings_changed(self, match: Match) -> None: ...

    async def lifeline_used(self, used: LifelineUsed) -> None: ...

    async def timer_paused(self, match: Match, caller: Player) -> None: ...

    async def timer_resumed(self, match: Match) -> None: ...

    async def round_finished(self, match: Match) -> None: ...

    async def match_finished(self, match: Match) -> None: ...

    async def match_closed(self, match: Match) -> None:
        """The match is gone; its players are free to queue again."""
        ...

    # Chat
    async def chat_message_posted(
        self, match: Match, message: ChatMessage, unread_counts: dict[str, int]
    ) -> None: ...

    async def chat_unread_changed(self, player_id: str, count: int) -> None: ...

    async def chat_history(self, player_id: str, messages: list[ChatMessage]) -> None: ...

    async def chat_cleared(self, match: Match) -> None: ...
