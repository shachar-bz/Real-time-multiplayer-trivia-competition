"""Socket.IO handlers for connecting, the lobby, answers and lifelines.

Each handler only parses the incoming payload and calls one service method;
replies and broadcasts go out through the GameEvents publisher.
"""

import socketio

from trivia.api import serializers
from trivia.api.events import ClientEvent, ServerEvent
from trivia.config import Settings
from trivia.domain.lifelines import Lifeline
from trivia.services.game_service import GameService
from trivia.services.matchmaking import Matchmaker


def register_socket_handlers(
    sio: socketio.AsyncServer,
    *,
    settings: Settings,
    matchmaker: Matchmaker,
    game_service: GameService,
) -> None:
    # `auth` and `reason` are accepted so python-socketio never falls back to its
    # "legacy signature" retry, which would run a handler twice if it raised TypeError.
    async def connect(sid, environ, auth=None):
        await sio.emit(ServerEvent.CONNECTED, serializers.connected(sid, settings), to=sid)

    async def disconnect(sid, reason=None):
        await matchmaker.leave(sid)
        await game_service.player_disconnected(sid)

    async def join_queue(sid, data=None):
        payload = serializers.read_payload(data)
        await matchmaker.join(
            sid, payload.get("name", ""), payload.get("ride"), payload.get("paint")
        )

    async def leave_queue(sid, data=None):
        await matchmaker.leave(sid)

    async def answer(sid, data=None):
        payload = serializers.read_payload(data)
        option = str(payload.get("option", "")).upper()
        await game_service.submit_answer(sid, payload.get("questionId"), option)

    async def use_help(sid, data=None):
        payload = serializers.read_payload(data)
        lifeline = Lifeline.parse(payload.get("helpType", ""))
        if lifeline is not None:
            await game_service.use_lifeline(sid, lifeline, payload.get("questionId"))

    sio.on("connect", connect)
    sio.on("disconnect", disconnect)
    sio.on(ClientEvent.JOIN_QUEUE, join_queue)
    sio.on(ClientEvent.LEAVE_QUEUE, leave_queue)
    sio.on(ClientEvent.ANSWER, answer)
    sio.on(ClientEvent.USE_HELP, use_help)
