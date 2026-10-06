"""Contract test: the server must speak exactly the wire protocol of the original server.

`protocol_baseline.json` was captured from the original (pre-refactor) server
and is frozen. The frontend is built against it, so this test fails on any
drift in event names, payload shapes, or the order in which a client receives
events. If it fails, fix the server, not the baseline.
"""

import asyncio
import json
import sqlite3
from pathlib import Path

import pytest
from aiohttp import web

from tests.contract import protocol_driver as driver

BASELINE = json.loads(Path(__file__).with_name("protocol_baseline.json").read_text())


def build_original_app(workdir: Path) -> web.Application:
    """Import the original module-level server with contract timings and test doubles."""
    sounds_dir = workdir / "sounds"
    sounds_dir.mkdir()
    (sounds_dir / "win_game.mp3").write_bytes(b"ID3")

    question_db = workdir / "trivia.db"
    with sqlite3.connect(question_db) as connection:
        connection.execute(
            """
            CREATE TABLE questions (
                id INTEGER PRIMARY KEY, topic TEXT, difficulty INTEGER, question TEXT,
                option_a TEXT, option_b TEXT, option_c TEXT, option_d TEXT, correct_option TEXT
            )
            """
        )
        connection.executemany(
            "INSERT INTO questions VALUES (:id, :topic, :difficulty, :question, "
            ":option_a, :option_b, :option_c, :option_d, :correct_option)",
            driver.CONTRACT_QUESTIONS,
        )

    import sound_events

    sound_events.SOUNDS_DIR = sounds_dir

    import chat
    import chat_db

    chat_db.CHAT_DB_PATH = workdir / "chat.db"
    chat_db.init_chat_db()
    chat.CHAT_DB_PATH = chat_db.CHAT_DB_PATH

    import bot

    for level in bot.DIFFICULTY_SETTINGS.values():
        level["accuracy"] = 1.0
        level["delay_min"], level["delay_max"] = driver.BOT_DELAY_SECONDS

    import server

    server.DB_PATH = question_db
    server.MATCHMAKING_SECONDS = driver.MATCHMAKING_SECONDS
    server.QUESTION_SECONDS = driver.QUESTION_SECONDS
    server.QUESTIONS_PER_GAME = driver.QUESTIONS_PER_GAME
    server.RESULT_SECONDS = driver.RESULT_SECONDS
    server.RACE_FINISH_SCORE = (driver.QUESTIONS_PER_GAME + 1) * server.MAX_SCORE_PER_QUESTION

    async def fake_friend(question, confidence):
        await asyncio.sleep(driver.FRIEND_DELAY_SECONDS)
        return "fake friend says C"

    server.call_a_friend = fake_friend
    return server.app


async def serve_and_record(app: web.Application) -> driver.ProtocolRecording:
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    try:
        return await driver.record_protocol(f"http://127.0.0.1:{port}")
    finally:
        await runner.cleanup()


@pytest.fixture(scope="module")
def recording(tmp_path_factory) -> driver.ProtocolRecording:
    app = build_original_app(tmp_path_factory.mktemp("contract"))
    return asyncio.run(serve_and_record(app))


def test_emits_exactly_the_baseline_event_names(recording):
    assert sorted(recording.shapes) == sorted(BASELINE["events"])


@pytest.mark.parametrize("event", sorted(BASELINE["events"]))
def test_event_payload_shapes_match_baseline(recording, event):
    expected = {json.dumps(payload_shape, sort_keys=True) for payload_shape in BASELINE["events"][event]}
    assert recording.shapes[event] == expected


@pytest.mark.parametrize("client", sorted(BASELINE["sequences"]))
def test_client_event_sequence_matches_baseline(recording, client):
    assert recording.sequences[client] == BASELINE["sequences"][client]


def test_http_routes_match_baseline(recording):
    assert recording.http == BASELINE["http"]
