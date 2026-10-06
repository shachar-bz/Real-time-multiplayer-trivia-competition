"""In-game chat messages."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatMessage:
    id: int
    game_id: str
    user_id: str
    username: str
    content: str
    timestamp: str  # "HH:MM" (UTC), as shown next to the message
