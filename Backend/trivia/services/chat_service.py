"""In-game chat: messages between the players of one match, with unread counters."""

from trivia.domain.match import Match
from trivia.services.ports import ChatStore, GameEvents
from trivia.services.registry import GameRegistry


class ChatService:
    def __init__(self, *, store: ChatStore, registry: GameRegistry, events: GameEvents):
        self._store = store
        self._registry = registry
        self._events = events

    async def send_message(self, player_id: str, game_id: object, content: object) -> None:
        match = self._registry.get(game_id)
        if match is None or player_id not in match.players or content is None:
            return

        sender = match.players[player_id]
        message = await self._store.save_message(match.id, player_id, sender.name, content)
        readers = [
            player.id
            for player in match.players.values()
            if player.id != player_id and not player.is_bot
        ]
        unread_counts = await self._store.add_unread(match.id, readers)
        await self._events.chat_message_posted(match, message, unread_counts)

    async def open_chat(self, player_id: str, game_id: object) -> None:
        """The player is looking at the chat: nothing is unread any more."""
        await self._store.clear_unread(game_id, player_id)
        await self._events.chat_unread_changed(player_id, 0)

    async def send_history(self, player_id: str, game_id: object) -> None:
        messages = await self._store.history(game_id)
        await self._events.chat_history(player_id, messages)

    async def close_chat(self, match: Match) -> None:
        """The match is over: clear the players' chat and forget its messages."""
        await self._events.chat_cleared(match)
        await self._store.delete_game(match.id)
