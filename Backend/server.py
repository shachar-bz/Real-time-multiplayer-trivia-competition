import asyncio
import os
import random
import sqlite3
import time
import uuid
from pathlib import Path

import socketio
from aiohttp import web


HOST = "0.0.0.0"
PORT = 8080
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "trivia.db"
MATCHMAKING_SECONDS = 30
QUESTION_SECONDS = 12
QUESTIONS_PER_GAME = 10
RESULT_SECONDS = 3
CLIENT_URL = os.getenv("CLIENT_URL", "http://localhost:8081")
VALID_OPTIONS = {"A", "B", "C", "D"}


sio = socketio.AsyncServer(async_mode="aiohttp", cors_allowed_origins=[CLIENT_URL, "*"])
app = web.Application()
sio.attach(app)

waiting_players = {}
matchmaking_task = None
matchmaking_started_at = None
games = {}
player_games = {}


def load_questions(limit):
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT id, topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option
            FROM questions
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    if len(rows) < limit:
        raise RuntimeError(f"Expected at least {limit} questions in {DB_PATH}, found {len(rows)}.")

    return [dict(row) for row in rows]


def public_question(question, index):
    return {
        "id": question["id"],
        "index": index + 1,
        "total": QUESTIONS_PER_GAME,
        "topic": question["topic"],
        "difficulty": question["difficulty"],
        "text": question["question"],
        "seconds": QUESTION_SECONDS,
        "options": [
            {"key": "A", "text": question["option_a"]},
            {"key": "B", "text": question["option_b"]},
            {"key": "C", "text": question["option_c"]},
            {"key": "D", "text": question["option_d"]},
        ],
    }


def leaderboard_for(game):
    players = list(game["players"].values())
    players.sort(key=lambda player: (-player["score"], player["name"].lower()))
    return [
        {
            "id": player["sid"],
            "name": player["name"],
            "score": player["score"],
            "connected": player["connected"],
        }
        for player in players
    ]


def waiting_status(start_time):
    seconds_passed = time.monotonic() - start_time
    seconds_left = max(0, MATCHMAKING_SECONDS - int(seconds_passed))
    return {
        "secondsLeft": seconds_left,
        "playerCount": len(waiting_players),
        "players": [player["name"] for player in waiting_players.values()],
    }


async def emit_waiting_status(start_time):
    if not waiting_players:
        return

    status = waiting_status(start_time)
    for sid in list(waiting_players):
        await sio.emit("matchmaking_status", status, to=sid)


async def matchmaking_countdown():
    global matchmaking_started_at, matchmaking_task

    matchmaking_started_at = time.monotonic()
    try:
        for _ in range(MATCHMAKING_SECONDS):
            await emit_waiting_status(matchmaking_started_at)
            await asyncio.sleep(1)

        await emit_waiting_status(matchmaking_started_at)
        players = dict(waiting_players)
        waiting_players.clear()

        if players:
            asyncio.create_task(run_game(players))
    finally:
        matchmaking_started_at = None
        matchmaking_task = None


async def run_game(players):
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "players": {},
        "questions": load_questions(QUESTIONS_PER_GAME),
        "current_index": -1,
        "accepting_answers": False,
        "answers": {},
    }
    games[game_id] = game

    for sid, player in players.items():
        game["players"][sid] = {
            "sid": sid,
            "name": player["name"],
            "score": 0,
            "connected": True,
        }
        player_games[sid] = game_id
        await sio.enter_room(sid, game_id)

    await sio.emit(
        "game_started",
        {
            "gameId": game_id,
            "players": [player["name"] for player in game["players"].values()],
            "questionCount": QUESTIONS_PER_GAME,
            "questionSeconds": QUESTION_SECONDS,
        },
        room=game_id,
    )

    for index, question in enumerate(game["questions"]):
        game["current_index"] = index
        game["answers"] = {}
        game["accepting_answers"] = True

        await sio.emit("question", public_question(question, index), room=game_id)
        await asyncio.sleep(QUESTION_SECONDS)

        game["accepting_answers"] = False
        correct_option = question["correct_option"].upper()
        answers = []

        for sid, player in game["players"].items():
            selected_option = game["answers"].get(sid)
            answers.append(
                {
                    "playerId": sid,
                    "name": player["name"],
                    "selectedOption": selected_option,
                    "isCorrect": selected_option == correct_option,
                }
            )

        await sio.emit(
            "question_result",
            {
                "questionId": question["id"],
                "correctOption": correct_option,
                "correctAnswer": question[f"option_{correct_option.lower()}"],
                "answers": answers,
                "leaderboard": leaderboard_for(game),
            },
            room=game_id,
        )
        await asyncio.sleep(RESULT_SECONDS)

    await sio.emit(
        "game_finished",
        {"leaderboard": leaderboard_for(game), "questionCount": QUESTIONS_PER_GAME},
        room=game_id,
    )

    for sid in list(game["players"]):
        player_games.pop(sid, None)
        await sio.leave_room(sid, game_id)
    games.pop(game_id, None)


@sio.event
async def connect(sid, environ):
    await sio.emit(
        "connected",
        {
            "sid": sid,
            "matchmakingSeconds": MATCHMAKING_SECONDS,
            "questionSeconds": QUESTION_SECONDS,
            "questionsPerGame": QUESTIONS_PER_GAME,
        },
        to=sid,
    )


@sio.event
async def disconnect(sid):
    waiting_players.pop(sid, None)
    if matchmaking_started_at is not None:
        await emit_waiting_status(matchmaking_started_at)

    game_id = player_games.get(sid)
    if game_id and game_id in games and sid in games[game_id]["players"]:
        games[game_id]["players"][sid]["connected"] = False


@sio.event
async def join_queue(sid, data):
    global matchmaking_started_at, matchmaking_task

    if sid in player_games:
        await sio.emit("error_message", {"message": "You are already in a game."}, to=sid)
        return

    raw_name = str((data or {}).get("name", "")).strip()
    player_name = raw_name[:24] or f"Player {random.randint(100, 999)}"
    waiting_players[sid] = {"sid": sid, "name": player_name}

    if matchmaking_task is None or matchmaking_task.done():
        matchmaking_task = asyncio.create_task(matchmaking_countdown())
        await asyncio.sleep(0)

    await emit_waiting_status(matchmaking_started_at or time.monotonic())


@sio.event
async def answer(sid, data):
    game_id = player_games.get(sid)
    if not game_id or game_id not in games:
        return

    game = games[game_id]
    if not game["accepting_answers"] or sid in game["answers"]:
        return

    selected_option = str((data or {}).get("option", "")).upper()
    question_id = (data or {}).get("questionId")
    current_question = game["questions"][game["current_index"]]

    if selected_option not in VALID_OPTIONS or question_id != current_question["id"]:
        return

    game["answers"][sid] = selected_option
    is_correct = selected_option == current_question["correct_option"].upper()
    if is_correct:
        game["players"][sid]["score"] += 1

    await sio.emit(
        "answer_received",
        {"questionId": question_id, "selectedOption": selected_option},
        to=sid,
    )


async def health(request):
    return web.json_response(
        {
            "status": "ok",
            "waitingPlayers": len(waiting_players),
            "activeGames": len(games),
            "dbPath": str(DB_PATH),
        }
    )


app.router.add_get("/", health)


if __name__ == "__main__":
    web.run_app(app, host=HOST, port=PORT)
