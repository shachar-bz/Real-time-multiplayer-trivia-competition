from bot import Bot
from player_profile import DEFAULT_PAINT, DEFAULT_RIDE, player_profile


HELP_FIFTY_FIFTY = "fifty_fifty"
HELP_DOUBLE_SCORE = "double_score"
HELP_CALL_A_FRIEND = "call_a_friend"


def default_human_helps():
    return {
        HELP_FIFTY_FIFTY: True,
        HELP_DOUBLE_SCORE: True,
        HELP_CALL_A_FRIEND: True,
    }


def is_bot_entry(player):
    return isinstance(player, Bot)


def player_dict_for_game(sid, player):
    if is_bot_entry(player):
        return player.to_player_dict()

    return {
        "sid": sid,
        "name": player["name"],
        "ride": player.get("ride", DEFAULT_RIDE),
        "paint": player.get("paint", DEFAULT_PAINT),
        "score": 0,
        "connected": True,
        "helps": default_human_helps(),
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
    leaderboard = []

    for player in players:
        profile = player_profile(player)
        leaderboard.append(
            {
                "id": player["sid"],
                "name": player["name"],
                "ride": player["ride"],
                "rideLabel": profile["rideLabel"],
                "paint": player["paint"],
                "paintLabel": profile["paintLabel"],
                "paintHex": profile["paintHex"],
                "score": player["score"],
                "connected": player["connected"],
            }
        )

    return leaderboard


def game_started_players(game):
    return [player_profile(player) for player in game["players"].values()]


def game_started_player_names(game):
    return [player["name"] for player in game["players"].values()]
