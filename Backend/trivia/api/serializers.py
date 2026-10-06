"""Wire payloads: pure functions from domain objects to the JSON the frontend reads.

Key names and value types are part of the frozen protocol
(tests/contract/protocol_baseline.json). Game payloads use camelCase; chat
payloads keep the snake_case keys the chat client was built with.
"""

from pathlib import Path

from trivia.config import Settings
from trivia.domain.chat import ChatMessage
from trivia.domain.lifelines import Lifeline
from trivia.domain.match import AnswerOutcome, LifelineUsed, Match
from trivia.domain.players import Player
from trivia.domain.questions import OPTION_KEYS
from trivia.domain.vehicles import (
    DEFAULT_PAINT,
    DEFAULT_RIDE,
    PAINTS,
    RIDES,
    normalize_paint,
    normalize_ride,
)

FRIEND_CALL_MESSAGE = "someone is calling his friend"


def read_payload(data: object) -> dict:
    """Incoming event data as a dict; anything else counts as an empty request."""
    return data if isinstance(data, dict) else {}


# Lobby and players ------------------------------------------------------------


def connected(sid: str, settings: Settings) -> dict:
    return {
        "sid": sid,
        "matchmakingSeconds": settings.matchmaking_seconds,
        "questionSeconds": settings.question_seconds,
        "questionsPerGame": settings.questions_per_game,
        "profileChoices": profile_choices(),
    }


def profile_choices() -> dict:
    return {
        "rides": [{"id": ride.id, "label": ride.label} for ride in RIDES.values()],
        "paints": [
            {"id": paint.id, "label": paint.label, "hex": paint.hex} for paint in PAINTS.values()
        ],
        "defaults": {"ride": DEFAULT_RIDE, "paint": DEFAULT_PAINT},
    }


def profile(player: Player) -> dict:
    ride = RIDES[normalize_ride(player.ride)]
    paint = PAINTS[normalize_paint(player.paint)]
    return {
        "id": player.id,
        "name": player.name,
        "ride": ride.id,
        "rideLabel": ride.label,
        "paint": paint.id,
        "paintLabel": paint.label,
        "paintHex": paint.hex,
        "isBot": player.is_bot,
    }


def helps(player: Player) -> dict:
    return {
        "fiftyFifty": player.has_lifeline(Lifeline.FIFTY_FIFTY),
        "doubleScore": player.has_lifeline(Lifeline.DOUBLE_SCORE),
        "callFriend": player.has_lifeline(Lifeline.CALL_A_FRIEND),
    }


def lobby_status(waiting: list[Player], seconds_left: int) -> dict:
    return {
        "secondsLeft": seconds_left,
        "playerCount": len(waiting),
        "players": [player.name for player in waiting],
        "playerProfiles": [profile(player) for player in waiting],
    }


def error(message: str) -> dict:
    return {"message": message}


# Match ------------------------------------------------------------------------


def game_started(match: Match) -> dict:
    return {
        "gameId": match.id,
        "players": [player.name for player in match.players.values()],
        "playerProfiles": [profile(player) for player in match.players.values()],
        "questionCount": match.question_count,
        "questionSeconds": match.question_seconds,
        "raceStandings": race_standings(match),
    }


def player_state(player: Player) -> dict:
    return {"helps": helps(player), "profile": profile(player)}


def race_standings(match: Match) -> dict:
    finish_score = max(1, match.finish_score)
    standings = []
    for player in match.players.values():
        racer = profile(player)
        standings.append(
            {
                "id": player.id,
                "name": player.name,
                "ride": racer["ride"],
                "rideLabel": racer["rideLabel"],
                "paint": racer["paint"],
                "paintLabel": racer["paintLabel"],
                "paintHex": racer["paintHex"],
                "score": player.score,
                "progressRatio": max(0, min(1, player.score / finish_score)),
                "connected": player.connected,
                "isBot": player.is_bot,
            }
        )
    return {"finishScore": match.finish_score, "players": standings}


def leaderboard(match: Match) -> list[dict]:
    rows = []
    for player in match.leaderboard():
        racer = profile(player)
        rows.append(
            {
                "id": player.id,
                "name": player.name,
                "ride": player.ride,
                "rideLabel": racer["rideLabel"],
                "paint": player.paint,
                "paintLabel": racer["paintLabel"],
                "paintHex": racer["paintHex"],
                "score": player.score,
                "connected": player.connected,
            }
        )
    return rows


def question(match: Match) -> dict:
    round_ = match.round
    return {
        "id": round_.question.id,
        "index": round_.number,
        "total": match.question_count,
        "topic": round_.question.topic,
        "difficulty": round_.question.difficulty,
        "text": round_.question.text,
        "seconds": match.question_seconds,
        "options": [{"key": key, "text": round_.question.options[key]} for key in OPTION_KEYS],
    }


def answer_received(outcome: AnswerOutcome) -> dict:
    return {"questionId": outcome.question.id, "selectedOption": outcome.option}


def help_used(used: LifelineUsed) -> dict:
    payload = {"helpType": used.lifeline.value, "questionId": used.question.id}
    if used.lifeline is Lifeline.FIFTY_FIFTY:
        payload["removedOptions"] = list(used.removed_options)
    elif used.lifeline is Lifeline.CALL_A_FRIEND:
        payload["confidence"] = used.friend_reply.confidence
        payload["message"] = used.friend_reply.message
        payload["friendAnswered"] = used.friend_reply.answered
    else:
        payload["doubleScoreActive"] = True
    payload["helps"] = helps(used.player)
    return payload


def timer_paused(match: Match, caller: Player) -> dict:
    return {
        "questionId": match.round.question.id,
        "secondsLeft": match.round.timer.seconds_left(),
        "callerId": caller.id,
        "callerName": caller.name,
        "message": FRIEND_CALL_MESSAGE,
    }


def timer_resumed(match: Match) -> dict:
    return {
        "questionId": match.round.question.id,
        "secondsLeft": match.round.timer.seconds_left(),
    }


def question_result(match: Match) -> dict:
    asked = match.round.question
    return {
        "questionId": asked.id,
        "correctOption": asked.correct_option,
        "correctAnswer": asked.correct_answer,
        "answers": [
            {
                "playerId": result.player.id,
                "name": result.player.name,
                "ride": result.player.ride,
                "paint": result.player.paint,
                "selectedOption": result.selected_option,
                "isCorrect": result.is_correct,
                "doubleScoreUsed": result.double_score_used,
                "pointsEarned": result.points_earned,
            }
            for result in match.round_results()
        ],
        "leaderboard": leaderboard(match),
        "raceStandings": race_standings(match),
    }


def game_finished(match: Match) -> dict:
    return {
        "leaderboard": leaderboard(match),
        "questionCount": match.question_count,
        "raceStandings": race_standings(match),
    }


# Chat -------------------------------------------------------------------------


def chat_message(message: ChatMessage) -> dict:
    return {
        "id": message.id,
        "game_id": message.game_id,
        "user_id": message.user_id,
        "username": message.username,
        "content": message.content,
        "timestamp": message.timestamp,
    }


def chat_history(messages: list[ChatMessage], reader_id: str) -> list[dict]:
    return [
        {
            "id": message.id,
            "username": message.username,
            "content": message.content,
            "timestamp": message.timestamp,
            "is_own": message.user_id == reader_id,
        }
        for message in messages
    ]


def unread_count(count: int) -> dict:
    return {"unread_count": count}


# HTTP -------------------------------------------------------------------------


def health(*, waiting_players: int, active_games: int, db_path: Path) -> dict:
    return {
        "status": "ok",
        "waitingPlayers": waiting_players,
        "activeGames": active_games,
        "dbPath": str(db_path),
    }
