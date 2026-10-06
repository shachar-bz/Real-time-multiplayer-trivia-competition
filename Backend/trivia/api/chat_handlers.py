"""Socket.IO handlers for the in-game chat."""

import socketio

from trivia.api import serializers
from trivia.api.events import ClientEvent
from trivia.services.chat_service import ChatService


def register_chat_handlers(sio: socketio.AsyncServer, chat: ChatService) -> None:
    async def chat_send_message(sid, data=None):
        payload = serializers.read_payload(data)
        await chat.send_message(sid, payload.get("game_id"), payload.get("content"))

    async def chat_open(sid, data=None):
        await chat.open_chat(sid, serializers.read_payload(data).get("game_id"))

    async def chat_request_history(sid, data=None):
        await chat.send_history(sid, serializers.read_payload(data).get("game_id"))

    sio.on(ClientEvent.CHAT_SEND_MESSAGE, chat_send_message)
    sio.on(ClientEvent.CHAT_OPEN, chat_open)
    sio.on(ClientEvent.CHAT_REQUEST_HISTORY, chat_request_history)
