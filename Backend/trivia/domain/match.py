"""The Match aggregate: every rule of a running game in one place.

A match plays a fixed list of questions, one round at a time. The service layer
decides *when* a round starts and ends; the match decides what is allowed while
it runs.

Requests a player should be told about raise `GameRuleError`. Requests the game
silently ignores (a stale question id, a second answer, an unknown option, ...)
return None and change nothing.
"""

import random
from dataclasses import dataclass, field

from trivia.domain.lifelines import Lifeline, options_to_remove
from trivia.domain.players import Player
from trivia.domain.questions import OPTION_KEYS, Question
from trivia.domain.scoring import points_for_answer, race_finish_score
from trivia.domain.timer import Clock, QuestionTimer

LIFELINE_ALREADY_USED = "You already used that help."
FRIEND_CALL_IN_PROGRESS = "Someone is already calling a friend."
TIMER_COULD_NOT_PAUSE = "The question timer could not pause."


class GameRuleError(Exception):
    """A request broke a game rule. The message is meant for the player."""


@dataclass(eq=False)
class Round:
    number: int  # 1-based
    question: Question
    timer: QuestionTimer
    answers: dict[str, str] = field(default_factory=dict)  # player id -> option
    points: dict[str, int] = field(default_factory=dict)  # player id -> points earned
    double_score_players: set[str] = field(default_factory=set)
    removed_options: dict[str, set[str]] = field(default_factory=dict)  # by fifty-fifty
    accepting_answers: bool = True
    friend_call_in_progress: bool = False

    def is_open_for(self, player_id: str) -> bool:
        return self.accepting_answers and player_id not in self.answers


@dataclass(frozen=True)
class AnswerOutcome:
    player: Player
    question: Question
    option: str
    points: int


@dataclass(frozen=True)
class FriendReply:
    confidence: int
    message: str
    answered: bool


@dataclass(frozen=True)
class LifelineUsed:
    player: Player
    lifeline: Lifeline
    question: Question
    removed_options: tuple[str, ...] = ()  # fifty-fifty only
    friend_reply: FriendReply | None = None  # call-a-friend only, once the friend replied


@dataclass(frozen=True)
class PlayerRoundResult:
    player: Player
    selected_option: str | None
    is_correct: bool
    double_score_used: bool
    points_earned: int


class Match:
    def __init__(
        self,
        match_id: str,
        players: list[Player],
        questions: list[Question],
        *,
        question_seconds: float,
        clock: Clock,
    ):
        if not questions:
            raise ValueError("A match needs at least one question.")
        self.id = match_id
        self.players: dict[str, Player] = {player.id: player for player in players}
        self.questions = list(questions)
        self.question_seconds = question_seconds
        self.finish_score = race_finish_score(len(self.questions))
        self.round: Round | None = None
        self._clock = clock

    @property
    def question_count(self) -> int:
        return len(self.questions)

    @property
    def humans(self) -> list[Player]:
        return [player for player in self.players.values() if not player.is_bot]

    # Rounds ----------------------------------------------------------------

    def start_next_round(self) -> Round | None:
        """Open the next question with a fresh timer, or return None when done."""
        number = 1 if self.round is None else self.round.number + 1
        if number > len(self.questions):
            return None

        timer = QuestionTimer(self.question_seconds, self._clock)
        timer.start()
        self.round = Round(number=number, question=self.questions[number - 1], timer=timer)
        return self.round

    def close_round(self) -> None:
        if self.round is not None:
            self.round.accepting_answers = False

    def all_connected_players_answered(self) -> bool:
        if self.round is None:
            return False
        connected = [player.id for player in self.players.values() if player.connected]
        return bool(connected) and all(player_id in self.round.answers for player_id in connected)

    def round_results(self) -> list[PlayerRoundResult]:
        round_ = self.round
        if round_ is None:
            return []
        return [
            PlayerRoundResult(
                player=player,
                selected_option=round_.answers.get(player.id),
                is_correct=round_.question.is_correct(round_.answers.get(player.id)),
                double_score_used=player.id in round_.double_score_players,
                points_earned=round_.points.get(player.id, 0),
            )
            for player in self.players.values()
        ]

    # Answers ---------------------------------------------------------------

    def submit_answer(
        self, player_id: str, question_id: object, option: str
    ) -> AnswerOutcome | None:
        """Record an answer and score it; None when the answer does not count."""
        round_ = self.round
        player = self.players.get(player_id)
        if round_ is None or player is None or not round_.is_open_for(player_id):
            return None
        if option not in OPTION_KEYS or question_id != round_.question.id:
            return None
        if option in round_.removed_options.get(player_id, set()):
            return None

        round_.answers[player_id] = option
        points = points_for_answer(
            is_correct=round_.question.is_correct(option),
            double_score=player_id in round_.double_score_players,
            remaining_seconds=round_.timer.remaining(),
            total_seconds=self.question_seconds,
        )
        player.score += points
        round_.points[player_id] = points
        return AnswerOutcome(player=player, question=round_.question, option=option, points=points)

    # Lifelines -------------------------------------------------------------

    def use_lifeline(
        self,
        player_id: str,
        lifeline: Lifeline,
        question_id: object,
        rng: random.Random,
    ) -> LifelineUsed | None:
        """Spend a lifeline on the current question.

        Calling a friend only *starts* the call: it pauses the timer, and the
        caller must later call `end_friend_call`.
        """
        round_ = self.round
        player = self.players.get(player_id)
        if round_ is None or player is None or not round_.is_open_for(player_id):
            return None
        if question_id != round_.question.id:
            return None
        if not player.has_lifeline(lifeline):
            raise GameRuleError(LIFELINE_ALREADY_USED)
        if lifeline is Lifeline.CALL_A_FRIEND and round_.friend_call_in_progress:
            raise GameRuleError(FRIEND_CALL_IN_PROGRESS)

        player.lifelines.discard(lifeline)
        if lifeline is Lifeline.FIFTY_FIFTY:
            removed = options_to_remove(round_.question, rng)
            round_.removed_options[player_id] = set(removed)
            return LifelineUsed(player, lifeline, round_.question, removed_options=tuple(removed))
        if lifeline is Lifeline.DOUBLE_SCORE:
            round_.double_score_players.add(player_id)
            return LifelineUsed(player, lifeline, round_.question)
        return self._start_friend_call(round_, player)

    def _start_friend_call(self, round_: Round, player: Player) -> LifelineUsed:
        round_.friend_call_in_progress = True
        if not round_.timer.pause():
            round_.friend_call_in_progress = False
            player.lifelines.add(Lifeline.CALL_A_FRIEND)
            raise GameRuleError(TIMER_COULD_NOT_PAUSE)
        return LifelineUsed(player, Lifeline.CALL_A_FRIEND, round_.question)

    def end_friend_call(self, round_: Round) -> bool:
        """Resume the countdown a friend call paused.

        Returns False when there is nothing to resume, for example because the
        call outlived the round it was made in.
        """
        if round_ is not self.round or not round_.accepting_answers:
            return False
        if not round_.timer.resume():
            return False
        round_.friend_call_in_progress = False
        return True

    def refund_lifeline(self, player_id: str, lifeline: Lifeline) -> None:
        player = self.players.get(player_id)
        if player is not None:
            player.lifelines.add(lifeline)

    # Players ---------------------------------------------------------------

    def mark_disconnected(self, player_id: str) -> bool:
        player = self.players.get(player_id)
        if player is None:
            return False
        player.connected = False
        return True

    def leaderboard(self) -> list[Player]:
        """Highest score first; ties in alphabetical order (case-insensitive)."""
        return sorted(
            self.players.values(),
            key=lambda player: (-player.score, player.name.lower()),
        )

    def winners(self) -> list[Player]:
        """Everyone sharing the top score."""
        ranking = self.leaderboard()
        if not ranking:
            return []
        return [player for player in ranking if player.score == ranking[0].score]
