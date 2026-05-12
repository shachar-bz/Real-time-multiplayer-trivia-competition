import asyncio
import math
import os
import random
import sqlite3
import time
import uuid
from pathlib import Path

import socketio
from aiohttp import web
from dotenv import load_dotenv

from bot import Bot, BotFactory
from chat import delete_game_chat, register_chat_handlers
from friend_agent import call_a_friend
from helpers import points_for_answer
from sound_events import (
    SOUND_SUBMIT_ANSWER,
    SOUND_WIN_GAME,
    emit_sound_to_room,
    emit_sound_to_user,
    register_sound_routes,
)


HOST = "0.0.0.0"
PORT = 8080
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DB_PATH = BASE_DIR / "trivia.db"
MATCHMAKING_SECONDS = 5
QUESTION_SECONDS = 20
QUESTIONS_PER_GAME = 10
RESULT_SECONDS = 3
CLIENT_URL = os.getenv("CLIENT_URL", "http://localhost:8081")
VALID_OPTIONS = {"A", "B", "C", "D"}
HELP_FIFTY_FIFTY = "fifty_fifty"
HELP_DOUBLE_SCORE = "double_score"
HELP_CALL_A_FRIEND = "call_a_friend"
HELP_TYPES = {HELP_FIFTY_FIFTY, HELP_DOUBLE_SCORE, HELP_CALL_A_FRIEND}
CALL_A_FRIEND_MIN_CONFIDENCE = 30
CALL_A_FRIEND_MAX_CONFIDENCE = 100
CALL_A_FRIEND_TIMEOUT_SECONDS = 10


sio = socketio.AsyncServer(async_mode="aiohttp", cors_allowed_origins=[CLIENT_URL, "*"])
app = web.Application()
sio.attach(app)

waiting_players = {}
matchmaking_task = None
matchmaking_started_at = None
games = {}
player_games = {}
register_chat_handlers(sio, games)


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


def player_helps(player):
    return {
        "fiftyFifty": player["helps"][HELP_FIFTY_FIFTY],
        "doubleScore": player["helps"][HELP_DOUBLE_SCORE],
        "callFriend": player["helps"][HELP_CALL_A_FRIEND],
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


def seconds_left_for_game(game):
    if game["question_timer_paused"]:
        return math.ceil(game["timer_remaining_seconds"])

    return max(0, math.ceil(game["question_deadline"] - time.monotonic()))


def all_connected_players_answered(game):
    connected_player_ids = [
        sid for sid, player in game["players"].items() if player["connected"]
    ]
    return bool(connected_player_ids) and all(
        sid in game["answers"] for sid in connected_player_ids
    )


async def pause_question_timer(game, caller_sid):
    async with game["timer_lock"]:
        if game["question_timer_paused"]:
            return False

        game["timer_remaining_seconds"] = max(
            0,
            game["question_deadline"] - time.monotonic(),
        )
        game["question_timer_paused"] = True
        game["question_deadline"] = None
        caller = game["players"][caller_sid]
        current_question = game["questions"][game["current_index"]]

    await sio.emit(
        "question_timer_paused",
        {
            "questionId": current_question["id"],
            "secondsLeft": seconds_left_for_game(game),
            "callerId": caller_sid,
            "callerName": caller["name"],
            "message": "someone is calling his friend",
        },
        room=game["id"],
    )
    return True


async def resume_question_timer(game):
    async with game["timer_lock"]:
        if not game["question_timer_paused"]:
            return

        game["question_deadline"] = time.monotonic() + game["timer_remaining_seconds"]
        game["question_timer_paused"] = False
        game["call_friend_in_progress"] = False
        current_question = game["questions"][game["current_index"]]

    await sio.emit(
        "question_timer_resumed",
        {
            "questionId": current_question["id"],
            "secondsLeft": seconds_left_for_game(game),
        },
        room=game["id"],
    )


async def wait_for_question_timer(game):
    while game["timer_remaining_seconds"] > 0:
        if all_connected_players_answered(game):
            break

        if game["question_timer_paused"]:
            await asyncio.sleep(0.1)
            continue

        game["timer_remaining_seconds"] = max(
            0,
            game["question_deadline"] - time.monotonic(),
        )
        if game["timer_remaining_seconds"] <= 0:
            break

        await asyncio.sleep(min(0.1, game["timer_remaining_seconds"]))


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
            if len(players) == 1:
                for bot in BotFactory.create_bots_for_solo_game():
                    players[bot.sid] = bot

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
        "double_score_players": set(),
        "removed_options_by_player": {},
        "question_deadline": None,
        "question_timer_paused": False,
        "timer_remaining_seconds": QUESTION_SECONDS,
        "timer_lock": asyncio.Lock(),
        "call_friend_in_progress": False,
    }
    games[game_id] = game

    for sid, player in players.items():
        if isinstance(player, Bot):
            game["players"][sid] = player.to_player_dict()
        else:
            game["players"][sid] = {
                "sid": sid,
                "name": player["name"],
                "score": 0,
                "connected": True,
                "helps": {
                    HELP_FIFTY_FIFTY: True,
                    HELP_DOUBLE_SCORE: True,
                    HELP_CALL_A_FRIEND: True,
                },
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
    for sid, player in game["players"].items():
        if not isinstance(players[sid], Bot):
            await sio.emit("player_state", {"helps": player_helps(player)}, to=sid)

    for index, question in enumerate(game["questions"]):
        game["current_index"] = index
        game["answers"] = {}
        game["double_score_players"] = set()
        game["removed_options_by_player"] = {}
        game["question_deadline"] = time.monotonic() + QUESTION_SECONDS
        game["question_timer_paused"] = False
        game["timer_remaining_seconds"] = QUESTION_SECONDS
        game["call_friend_in_progress"] = False
        game["accepting_answers"] = True

        await sio.emit("question", public_question(question, index), room=game_id)
        for sid, player in game["players"].items():
            if isinstance(players[sid], Bot):
                asyncio.create_task(
                    players[sid].answer(
                        game,
                        question["correct_option"].upper(),
                        VALID_OPTIONS,
                    )
                )

        await wait_for_question_timer(game)

        game["accepting_answers"] = False
        correct_option = question["correct_option"].upper()
        answers = []

        for sid, player in game["players"].items():
            selected_option = game["answers"].get(sid)
            is_correct = selected_option == correct_option
            used_double_score = sid in game["double_score_players"]
            points_earned = points_for_answer(selected_option, correct_option, used_double_score)
            answers.append(
                {
                    "playerId": sid,
                    "name": player["name"],
                    "selectedOption": selected_option,
                    "isCorrect": is_correct,
                    "doubleScoreUsed": used_double_score,
                    "pointsEarned": points_earned,
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

    final_leaderboard = leaderboard_for(game)
    await sio.emit(
        "game_finished",
        {"leaderboard": final_leaderboard, "questionCount": QUESTIONS_PER_GAME},
        room=game_id,
    )
    if final_leaderboard:
        winning_score = final_leaderboard[0]["score"]
        for player in final_leaderboard:
            if player["score"] == winning_score:
                await emit_sound_to_user(sio, player["id"], SOUND_WIN_GAME)
            else:
                break

    await sio.emit("chat_history_cleared", {}, room=game_id)

    for sid in list(game["players"]):
        if not isinstance(players[sid], Bot):
            player_games.pop(sid, None)
            await sio.leave_room(sid, game_id)
    await delete_game_chat(game_id)
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

    if selected_option in game["removed_options_by_player"].get(sid, set()):
        return

    game["answers"][sid] = selected_option
    correct_option = current_question["correct_option"].upper()
    used_double_score = sid in game["double_score_players"]
    points_earned = points_for_answer(selected_option, correct_option, used_double_score)
    game["players"][sid]["score"] += points_earned

    await emit_sound_to_room(sio, game_id, SOUND_SUBMIT_ANSWER)
    await sio.emit(
        "answer_received",
        {"questionId": question_id, "selectedOption": selected_option},
        to=sid,
    )


@sio.event
async def use_help(sid, data):
    game_id = player_games.get(sid)
    if not game_id or game_id not in games:
        return

    game = games[game_id]
    if not game["accepting_answers"] or sid in game["answers"]:
        return

    player = game["players"].get(sid)
    help_type = str((data or {}).get("helpType", ""))
    question_id = (data or {}).get("questionId")
    current_question = game["questions"][game["current_index"]]

    if not player or help_type not in HELP_TYPES or question_id != current_question["id"]:
        return

    if not player["helps"][help_type]:
        await sio.emit("error_message", {"message": "You already used that help."}, to=sid)
        return

    if help_type == HELP_CALL_A_FRIEND and game["call_friend_in_progress"]:
        await sio.emit("error_message", {"message": "Someone is already calling a friend."}, to=sid)
        return

    player["helps"][help_type] = False

    if help_type == HELP_FIFTY_FIFTY:
        correct_option = current_question["correct_option"].upper()
        wrong_options = [option for option in VALID_OPTIONS if option != correct_option]
        removed_options = random.sample(wrong_options, 2)
        game["removed_options_by_player"][sid] = set(removed_options)
        await sio.emit(
            "help_used",
            {
                "helpType": help_type,
                "questionId": question_id,
                "removedOptions": removed_options,
                "helps": player_helps(player),
            },
            to=sid,
        )
        return

    if help_type == HELP_CALL_A_FRIEND:
        game["call_friend_in_progress"] = True
        timer_paused = await pause_question_timer(game, sid)
        if not timer_paused:
            game["call_friend_in_progress"] = False
            player["helps"][help_type] = True
            await sio.emit("error_message", {"message": "The question timer could not pause."}, to=sid)
            return

        confidence = random.randint(CALL_A_FRIEND_MIN_CONFIDENCE, CALL_A_FRIEND_MAX_CONFIDENCE)
        try:
            friend_message = await asyncio.wait_for(
                call_a_friend(current_question, confidence),
                timeout=CALL_A_FRIEND_TIMEOUT_SECONDS,
            )
            friend_answered = True
        except asyncio.TimeoutError:
            friend_message = "friend is not answering right now"
            friend_answered = False
        except Exception as error:
            player["helps"][help_type] = True
            await resume_question_timer(game)
            await sio.emit("error_message", {"message": str(error)}, to=sid)
            return

        await sio.emit(
            "help_used",
            {
                "helpType": help_type,
                "questionId": question_id,
                "confidence": confidence,
                "message": friend_message,
                "friendAnswered": friend_answered,
                "helps": player_helps(player),
            },
            to=sid,
        )
        await resume_question_timer(game)
        return

    game["double_score_players"].add(sid)
    await sio.emit(
        "help_used",
        {
            "helpType": help_type,
            "questionId": question_id,
            "doubleScoreActive": True,
            "helps": player_helps(player),
        },
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
register_sound_routes(app)


if __name__ == "__main__":
    web.run_app(app, host=HOST, port=PORT)
