from bot import Bot


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
    return [
        {
            "id": player["sid"],
            "name": player["name"],
            "score": player["score"],
            "connected": player["connected"],
        }
        for player in players
    ]


def game_started_players(game):
    return [player["name"] for player in game["players"].values()]
