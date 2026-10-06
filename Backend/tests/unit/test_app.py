"""The composition root, started the way a fresh clone starts it.

`trivia.db` and `sounds/` are gitignored, so a fresh clone has neither. The app
must still start: it builds the question database from the shipped CSV and
simply does not serve sound files.
"""

from aiohttp.test_utils import TestClient, TestServer

from trivia.adapters.sqlite_questions import count_questions
from trivia.app import SERVICES, create_app
from trivia.config import Settings


def fresh_clone_settings(tmp_path) -> Settings:
    """The shipped questions CSV, but no question database and no sounds directory."""
    return Settings(
        question_db_path=tmp_path / "data" / "trivia.db",
        chat_db_path=tmp_path / "data" / "chat.db",
        sounds_dir=tmp_path / "sounds",
    )


async def test_a_fresh_clone_builds_its_question_database_on_startup(tmp_path):
    settings = fresh_clone_settings(tmp_path)
    app = create_app(settings)
    assert app[SERVICES].settings is settings

    async with TestClient(TestServer(app)) as client:
        response = await client.get("/")
        assert response.status == 200
        assert await response.json() == {
            "status": "ok",
            "waitingPlayers": 0,
            "activeGames": 0,
            "dbPath": str(settings.question_db_path),
        }

    assert count_questions(settings.question_db_path) >= settings.questions_per_game


async def test_sound_files_are_served_only_when_the_directory_exists(tmp_path):
    settings = fresh_clone_settings(tmp_path)
    async with TestClient(TestServer(create_app(settings))) as client:
        assert (await client.get("/sounds/win_game.mp3")).status == 404

    settings.sounds_dir.mkdir()
    (settings.sounds_dir / "win_game.mp3").write_bytes(b"ID3")
    async with TestClient(TestServer(create_app(settings))) as client:
        assert (await client.get("/sounds/win_game.mp3")).status == 200
