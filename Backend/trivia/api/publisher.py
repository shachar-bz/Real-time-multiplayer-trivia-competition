"""SocketIOGameEvents: the GameEvents port, implemented with Socket.IO emits.

This is where game events become wire events. It decides who hears what (the
whole match room or a single player), which sound effects play, and the order
of the emits, which is part of the frozen protocol.
"""

import logging

import socketio

from trivia.api import serializers
from trivia.api.events import ServerEvent
from trivia.api.sounds import Sound, sound_payload
from trivia.domain.chat import ChatMessage
from trivia.domain.match import AnswerOutcome, LifelineUsed, Match
from trivia.domain.players import Player

logger = logging.getLogger(__name__)


class SocketIOGameEvents:
    def __init__(self, sio: socketio.AsyncServer):
        self._sio = sio

    async def _to_player(self, player_id: str, event: ServerEvent, payload) -> None:
        await self._sio.emit(event, payload, to=player_id)

    async def _to_match(
        self, match: Match, event: ServerEvent, payload, skip: str | None = None
    ) -> None:
        await self._sio.emit(event, payload, room=match.id, skip_sid=skip)

    # Lobby -----------------------------------------------------------------

    async def lobby_updated(self, waiting: list[Player], seconds_left: int) -> None:
        status = serializers.lobby_status(waiting, seconds_left)
        for player in waiting:
            await self._to_player(player.id, ServerEvent.MATCHMAKING_STATUS, status)

    async def error(self, player_id: str, message: str) -> None:
        await self._to_player(player_id, ServerEvent.ERROR_MESSAGE, serializers.error(message))

    # Match flow ------------------------------------------------------------

    async def match_started(self, match: Match) -> None:
        for player in match.humans:
            try:
                await self._sio.enter_room(player.id, match.id)
            except (KeyError, ValueError):  # disconnected while the match was being set up
                logger.info("Player %s left before match %s started", player.id, match.id)

        await self._to_match(match, ServerEvent.GAME_STARTED, serializers.game_started(match))
        await self.standings_changed(match)
        for player in match.humans:
            state = serializers.player_state(player)
            await self._to_player(player.id, ServerEvent.PLAYER_STATE, state)

    async def question_started(self, match: Match) -> None:
        await self._to_match(match, ServerEvent.QUESTION, serializers.question(match))

    async def answer_accepted(self, match: Match, outcome: AnswerOutcome) -> None:
        await self._to_match(match, ServerEvent.SOUND_EFFECT, sound_payload(Sound.SUBMIT_ANSWER))
        await self._to_player(
            outcome.player.id, ServerEvent.ANSWER_RECEIVED, serializers.answer_received(outcome)
        )

    async def standings_changed(self, match: Match) -> None:
        await self._to_match(match, ServerEvent.RACE_STANDINGS, serializers.race_standings(match))

    async def lifeline_used(self, used: LifelineUsed) -> None:
        await self._to_player(used.player.id, ServerEvent.HELP_USED, serializers.help_used(used))

    async def timer_paused(self, match: Match, caller: Player) -> None:
        payload = serializers.timer_paused(match, caller)
        await self._to_match(match, ServerEvent.QUESTION_TIMER_PAUSED, payload)

    async def timer_resumed(self, match: Match) -> None:
        payload = serializers.timer_resumed(match)
        await self._to_match(match, ServerEvent.QUESTION_TIMER_RESUMED, payload)

    async def round_finished(self, match: Match) -> None:
        await self._to_match(match, ServerEvent.QUESTION_RESULT, serializers.question_result(match))

    async def match_finished(self, match: Match) -> None:
        await self._to_match(match, ServerEvent.GAME_FINISHED, serializers.game_finished(match))
        for winner in match.winners():
            if not winner.is_bot:
                await self._to_player(
                    winner.id, ServerEvent.SOUND_EFFECT, sound_payload(Sound.WIN_GAME)
                )

    async def match_closed(self, match: Match) -> None:
        for player in match.humans:
            await self._sio.leave_room(player.id, match.id)

    # Chat ------------------------------------------------------------------

    async def chat_message_posted(
        self, match: Match, message: ChatMessage, unread_counts: dict[str, int]
    ) -> None:
        await self._to_match(match, ServerEvent.CHAT_NEW_MESSAGE, serializers.chat_message(message))
        for player_id, count in unread_counts.items():
            await self.chat_unread_changed(player_id, count)
        await self._to_match(
            match, ServerEvent.SOUND_EFFECT, sound_payload(Sound.CHAT_MESSAGE), skip=message.user_id
        )

    async def chat_unread_changed(self, player_id: str, count: int) -> None:
        payload = serializers.unread_count(count)
        await self._to_player(player_id, ServerEvent.CHAT_UNREAD_UPDATE, payload)

    async def chat_history(self, player_id: str, messages: list[ChatMessage]) -> None:
        payload = serializers.chat_history(messages, player_id)
        await self._to_player(player_id, ServerEvent.CHAT_HISTORY, payload)

    async def chat_cleared(self, match: Match) -> None:
        await self._to_match(match, ServerEvent.CHAT_HISTORY_CLEARED, {})
