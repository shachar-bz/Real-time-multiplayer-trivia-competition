"""Contract test: the server must speak exactly the wire protocol of the original server.

`protocol_baseline.json` was captured from the original (pre-refactor) server
and is frozen. The frontend is built against it, so this test fails on any
drift in event names, payload shapes, or the order in which a client receives
events. If it fails, fix the server, not the baseline.
"""

import asyncio
import csv
import json
from pathlib import Path

import pytest
from aiohttp import web

from tests.contract import protocol_driver as driver
from trivia.app import create_app
from trivia.config import Settings
from trivia.domain.bots import DifficultyProfile

BASELINE = json.loads(Path(__file__).with_name("protocol_baseline.json").read_text())


class FakeFriend:
    async def advise(self, question, confidence):
        await asyncio.sleep(driver.FRIEND_DELAY_SECONDS)
        return "fake friend says C"


def build_app(workdir: Path) -> web.Application:
    """The real app with contract timings, fast always-correct bots and a fake friend.

    The question database does not exist yet: the app builds it from the CSV on
    startup, exactly like on a fresh clone.
    """
    sounds_dir = workdir / "sounds"
    sounds_dir.mkdir()
    (sounds_dir / "win_game.mp3").write_bytes(b"ID3")

    questions_csv = workdir / "questions.csv"
    with questions_csv.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(driver.CONTRACT_QUESTIONS[0]))
        writer.writeheader()
        writer.writerows(driver.CONTRACT_QUESTIONS)

    settings = Settings(
        question_db_path=workdir / "data" / "trivia.db",
        questions_csv_path=questions_csv,
        chat_db_path=workdir / "data" / "chat.db",
        sounds_dir=sounds_dir,
        matchmaking_seconds=driver.MATCHMAKING_SECONDS,
        question_seconds=driver.QUESTION_SECONDS,
        questions_per_game=driver.QUESTIONS_PER_GAME,
        result_seconds=driver.RESULT_SECONDS,
    )
    fast_bots = (DifficultyProfile("contract", 1.0, *driver.BOT_DELAY_SECONDS),)
    return create_app(settings, friend_advisor=FakeFriend(), bot_profiles=fast_bots)


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
    app = build_app(tmp_path_factory.mktemp("contract"))
    return asyncio.run(serve_and_record(app))


def test_emits_exactly_the_baseline_event_names(recording):
    assert sorted(recording.shapes) == sorted(BASELINE["events"])


@pytest.mark.parametrize("event", sorted(BASELINE["events"]))
def test_event_payload_shapes_match_baseline(recording, event):
    expected = {json.dumps(shape, sort_keys=True) for shape in BASELINE["events"][event]}
    assert recording.shapes[event] == expected


@pytest.mark.parametrize("client", sorted(BASELINE["sequences"]))
def test_client_event_sequence_matches_baseline(recording, client):
    assert recording.sequences[client] == BASELINE["sequences"][client]


def test_http_routes_match_baseline(recording):
    assert recording.http == BASELINE["http"]
