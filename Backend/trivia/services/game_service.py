"""Runs matches: rounds, answers, lifelines, bots and disconnects.

Each match runs in its own task:

    match_started
    for every question:
        question_started -> bots plan and answer -> wait until everyone
        connected has answered or the timer runs out -> round_finished -> pause
    match_finished -> chat closed -> match_closed

Player requests (answers, lifelines, disconnects) arrive concurrently from the
socket handlers. They change the Match and then wake the round loop, which
re-checks whether the round is over. The Match decides what is allowed; this
service only decides when things happen.
"""

import asyncio
import contextlib
import dataclasses
import logging
import random
import uuid
from dataclasses import dataclass, field

from trivia.domain.lifelines import Lifeline
from trivia.domain.match import FriendReply, GameRuleError, LifelineUsed, Match, Round
from trivia.domain.players import Player
from trivia.domain.questions import Question
from trivia.domain.timer import Clock
from trivia.services.chat_service import ChatService
from trivia.services.ports import FriendAdvisor, GameEvents, QuestionBank
from trivia.services.registry import GameRegistry

logger = logging.getLogger(__name__)

FRIEND_NOT_ANSWERING = "friend is not answering right now"
MATCH_COULD_NOT_START = "The game could not start. Please try again."


@dataclass(eq=False)
class RunningMatch:
    """A match plus the asyncio machinery that drives it."""

    match: Match
    round_changed: asyncio.Event = field(default_factory=asyncio.Event)
    bot_answers: set[asyncio.Task] = field(default_factory=set)


class GameService:
    def __init__(
        self,
        *,
        events: GameEvents,
        registry: GameRegistry,
        question_bank: QuestionBank,
        friend_advisor: FriendAdvisor,
        chat: ChatService,
        question_seconds: float,
        questions_per_game: int,
        result_seconds: float,
        friend_timeout_seconds: float,
        friend_confidence_range: tuple[int, int],
        clock: Clock,
        rng: random.Random,
    ):
        self._events = events
        self._registry = registry
        self._question_bank = question_bank
        self._friend_advisor = friend_advisor
        self._chat = chat
        self._question_seconds = question_seconds
        self._questions_per_game = questions_per_game
        self._result_seconds = result_seconds
        self._friend_timeout_seconds = friend_timeout_seconds
        self._friend_confidence_range = friend_confidence_range
        self._clock = clock
        self._rng = rng
        self._running: dict[str, RunningMatch] = {}
        self._match_tasks: set[asyncio.Task] = set()

    # Starting and running a match -------------------------------------------

    async def start_match(self, lineup: list[Player]) -> None:
        """Start a match for the lineup, or tell its players that it could not start.

        The questions are drawn before the match exists, so a failure leaves
        nothing half-started and the players are free to queue again.
        """
        try:
            questions = await self._question_bank.draw(self._questions_per_game)
        except Exception:
            logger.exception("Could not start a match for %s", [p.name for p in lineup])
            for player in lineup:
                if not player.is_bot:
                    await self._events.error(player.id, MATCH_COULD_NOT_START)
            return

        match = Match(
            str(uuid.uuid4()),
            lineup,
            questions,
            question_seconds=self._question_seconds,
            clock=self._clock,
        )
        self._registry.add(match)
        running = RunningMatch(match)
        self._running[match.id] = running

        task = asyncio.create_task(self._run(running))
        self._match_tasks.add(task)
        task.add_done_callback(self._match_tasks.discard)

    async def shutdown(self) -> None:
        """Stop every running match (used when the server stops)."""
        for task in list(self._match_tasks):
            task.cancel()
        await asyncio.gather(*self._match_tasks, return_exceptions=True)

    async def _run(self, running: RunningMatch) -> None:
        match = running.match
        logger.info("Match %s started: %s", match.id, [p.name for p in match.players.values()])
        try:
            await self._play(running)
        except Exception:
            logger.exception("Match %s stopped because of an error", match.id)
        finally:
            self._cancel_bot_answers(running)
            self._running.pop(match.id, None)
            self._registry.remove(match)

        try:
            await self._chat.close_chat(match)
            await self._events.match_closed(match)
        except Exception:
            logger.exception("Could not close match %s cleanly", match.id)

    async def _play(self, running: RunningMatch) -> None:
        match = running.match
        await self._events.match_started(match)

        while match.start_next_round() is not None:
            await self._events.question_started(match)
            self._schedule_bot_answers(running)
            await self._wait_for_round_end(running)
            self._cancel_bot_answers(running)
            match.close_round()
            await self._events.round_finished(match)
            await asyncio.sleep(self._result_seconds)

        await self._events.match_finished(match)
        logger.info("Match %s finished, winners: %s", match.id, [p.name for p in match.winners()])

    async def _wait_for_round_end(self, running: RunningMatch) -> None:
        """Sleep until every connected player answered or the (pausable) timer ran out."""
        match = running.match
        timer = match.round.timer
        while True:
            running.round_changed.clear()
            if match.all_connected_players_answered() or timer.expired:
                return
            timeout = None if timer.paused else timer.remaining()
            with contextlib.suppress(TimeoutError):
                await asyncio.wait_for(running.round_changed.wait(), timeout)

    # Bots ------------------------------------------------------------------

    def _schedule_bot_answers(self, running: RunningMatch) -> None:
        question = running.match.round.question
        for player in running.match.players.values():
            if player.brain is None:
                continue
            plan = player.brain.plan(question, self._rng)
            task = asyncio.create_task(
                self._answer_as_bot(running, player, question, plan.delay_seconds, plan.option)
            )
            running.bot_answers.add(task)
            task.add_done_callback(running.bot_answers.discard)

    async def _answer_as_bot(
        self, running: RunningMatch, bot: Player, question: Question, delay: float, option: str
    ) -> None:
        await asyncio.sleep(delay)
        if running.match.submit_answer(bot.id, question.id, option) is None:
            return
        await self._events.standings_changed(running.match)
        running.round_changed.set()

    def _cancel_bot_answers(self, running: RunningMatch) -> None:
        for task in list(running.bot_answers):
            task.cancel()

    # Player requests -------------------------------------------------------

    async def submit_answer(self, player_id: str, question_id: object, option: str) -> None:
        running = self._running_match_of(player_id)
        if running is None:
            return
        outcome = running.match.submit_answer(player_id, question_id, option)
        if outcome is None:
            return

        await self._events.answer_accepted(running.match, outcome)
        await self._events.standings_changed(running.match)
        running.round_changed.set()

    async def use_lifeline(self, player_id: str, lifeline: Lifeline, question_id: object) -> None:
        running = self._running_match_of(player_id)
        if running is None:
            return
        try:
            used = running.match.use_lifeline(player_id, lifeline, question_id, self._rng)
        except GameRuleError as error:
            await self._events.error(player_id, str(error))
            return
        if used is None:
            return

        if used.lifeline is Lifeline.CALL_A_FRIEND:
            await self._call_a_friend(running, used)
        else:
            await self._events.lifeline_used(used)

    async def player_disconnected(self, player_id: str) -> None:
        running = self._running_match_of(player_id)
        if running is None or not running.match.mark_disconnected(player_id):
            return

        await self._events.standings_changed(running.match)
        running.round_changed.set()

    def _running_match_of(self, player_id: str) -> RunningMatch | None:
        match = self._registry.match_for_player(player_id)
        return self._running.get(match.id) if match is not None else None

    # Phone a friend --------------------------------------------------------

    async def _call_a_friend(self, running: RunningMatch, used: LifelineUsed) -> None:
        """The timer is paused while the friend thinks; the call belongs to its round."""
        match = running.match
        round_ = match.round
        caller = used.player
        await self._events.timer_paused(match, caller)
        running.round_changed.set()

        confidence = self._rng.randint(*self._friend_confidence_range)
        try:
            message = await asyncio.wait_for(
                self._friend_advisor.advise(used.question, confidence),
                timeout=self._friend_timeout_seconds,
            )
            answered = True
        except TimeoutError:
            message, answered = FRIEND_NOT_ANSWERING, False
        except Exception as error:
            logger.warning("Phone-a-friend failed: %s", error)
            match.refund_lifeline(caller.id, Lifeline.CALL_A_FRIEND)
            await self._resume_after_friend_call(running, round_)
            await self._events.error(caller.id, str(error))
            return

        reply = FriendReply(confidence=confidence, message=message, answered=answered)
        await self._events.lifeline_used(dataclasses.replace(used, friend_reply=reply))
        await self._resume_after_friend_call(running, round_)

    async def _resume_after_friend_call(self, running: RunningMatch, round_: Round) -> None:
        if running.match.end_friend_call(round_):
            await self._events.timer_resumed(running.match)
            running.round_changed.set()
