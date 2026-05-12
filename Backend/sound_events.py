from pathlib import Path


SOUNDS_DIR = Path(__file__).resolve().parent / "sounds"
SOUND_CORRECT_ANSWER = "correct_answer"
SOUND_WRONG_ANSWER = "wrong_answer"
SOUND_WIN_GAME = "win_game"
SOUND_SUBMIT_ANSWER = "submit_answer"
SOUND_CHAT_MESSAGE = "chat_message"
SOUND_FILES = {
    SOUND_CORRECT_ANSWER: "correct_answer.mp3",
    SOUND_WRONG_ANSWER: "wrong_answer.mp3",
    SOUND_WIN_GAME: "win_game.mp3",
    SOUND_SUBMIT_ANSWER: "submit_answer.mp3",
    SOUND_CHAT_MESSAGE: "chat_message.mp3",
}
SOUND_EVENT = "sound_effect"
SOUNDS_ROUTE = "/sounds"


def sound_payload(sound_name):
    return {
        "name": sound_name,
        "url": f"{SOUNDS_ROUTE}/{SOUND_FILES[sound_name]}",
    }


async def emit_sound_to_room(sio, room_id, sound_name, skip_sid=None):
    await sio.emit(SOUND_EVENT, sound_payload(sound_name), room=room_id, skip_sid=skip_sid)


async def emit_sound_to_user(sio, sid, sound_name):
    await sio.emit(SOUND_EVENT, sound_payload(sound_name), to=sid)


def register_sound_routes(app):
    app.router.add_static(SOUNDS_ROUTE, SOUNDS_DIR)
