"""In-game chat: messages between the players of one match, with unread counters.

A match's chat is private to its players: every request names a game id, and
requests from anyone who is not playing in that match are ignored.
"""

from trivia.domain.chat import clean_message
from trivia.domain.match import Match
from trivia.services.ports import ChatStore, GameEvents
from trivia.services.registry import GameRegistry


class ChatService:
    def __init__(self, *, store: ChatStore, registry: GameRegistry, events: GameEvents):
        self._store = store
        self._registry = registry
        self._events = events

    async def send_message(self, player_id: str, game_id: object, content: object) -> None:
        match = self._match_of_member(player_id, game_id)
        text = clean_message(content)
        if match is None or text is None:
            return

        sender = match.players[player_id]
        message = await self._store.save_message(match.id, player_id, sender.name, text)
        readers = [
            player.id
            for player in match.players.values()
            if player.id != player_id and not player.is_bot
        ]
        unread_counts = await self._store.add_unread(match.id, readers)
        await self._events.chat_message_posted(match, message, unread_counts)

    async def open_chat(self, player_id: str, game_id: object) -> None:
        """The player is looking at the chat: nothing is unread any more."""
        match = self._match_of_member(player_id, game_id)
        if match is None:
            return

        await self._store.clear_unread(match.id, player_id)
        await self._events.chat_unread_changed(player_id, 0)

    async def send_history(self, player_id: str, game_id: object) -> None:
        match = self._match_of_member(player_id, game_id)
        if match is None:
            return

        messages = await self._store.history(match.id)
        await self._events.chat_history(player_id, messages)

    async def close_chat(self, match: Match) -> None:
        """The match is over: clear the players' chat and forget its messages."""
        await self._events.chat_cleared(match)
        await self._store.delete_game(match.id)

    def _match_of_member(self, player_id: str, game_id: object) -> Match | None:
        """The running match `game_id` names, provided the player is in it."""
        match = self._registry.get(game_id)
        if match is None or player_id not in match.players:
            return None
        return match
