"""Sound effects the server tells clients to play, and the route serving the files."""

import logging
from enum import StrEnum
from pathlib import Path

from aiohttp import web

logger = logging.getLogger(__name__)

SOUNDS_ROUTE = "/sounds"


class Sound(StrEnum):
    SUBMIT_ANSWER = "submit_answer"  # to the match room when a human answers (bots are silent)
    CHAT_MESSAGE = "chat_message"  # to the match room except the sender
    WIN_GAME = "win_game"  # to each winner


def sound_payload(sound: Sound) -> dict:
    return {"name": sound.value, "url": f"{SOUNDS_ROUTE}/{sound.value}.mp3"}


def register_sound_route(app: web.Application, sounds_dir: Path) -> bool:
    """Serve `sounds_dir` at /sounds. The directory is optional (it is not in git)."""
    if not sounds_dir.is_dir():
        logger.warning("Sound directory %s not found: /sounds will not be served.", sounds_dir)
        return False

    app.router.add_static(SOUNDS_ROUTE, sounds_dir)
    return True
