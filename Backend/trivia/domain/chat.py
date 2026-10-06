"""In-game chat messages, and what counts as a message worth posting."""

from dataclasses import dataclass

# The chat box stops at 240 characters; anything far beyond that is not a real client.
MAX_MESSAGE_LENGTH = 500


@dataclass(frozen=True)
class ChatMessage:
    id: int
    game_id: str
    user_id: str
    username: str
    content: str
    timestamp: str  # "HH:MM" (UTC), as shown next to the message


def clean_message(content: object) -> str | None:
    """The text to post without surrounding whitespace, or None if it cannot be posted.

    Only non-empty text of at most MAX_MESSAGE_LENGTH characters is a message.
    """
    if not isinstance(content, str):
        return None
    text = content.strip()
    if not text or len(text) > MAX_MESSAGE_LENGTH:
        return None
    return text
