"""Wire payloads: key names and values the frontend reads.

The contract test pins every payload's shape end to end; these tests pin the
values that the shapes alone cannot show.
"""

import random

import pytest

from tests.fakes import FakeClock, make_question
from trivia.api import serializers
from trivia.config import Settings
from trivia.domain.bots import BotBrain, DifficultyProfile
from trivia.domain.chat import ChatMessage
from trivia.domain.lifelines import Lifeline
from trivia.domain.match import FriendReply, LifelineUsed, Match
from trivia.domain.players import Player


@pytest.fixture
def match():
    robot = Player.bot("bot-1", "Robo 🤖", "superbike", "blue",
                       BotBrain(DifficultyProfile("test", 1.0, 0, 0)))  # fmt: skip
    alice = Player.human("alice", "alice", "sportsCar", "pink")
    players = [alice, Player.human("bob", "Bob"), robot]
    questions = [make_question(7, correct_option="B"), make_question(8)]
    return Match("game-1", players, questions, question_seconds=20, clock=FakeClock())


def test_connected_announces_timings_and_profile_choices():
    payload = serializers.connected("sid-1", Settings())
    assert payload["sid"] == "sid-1"
    assert (payload["matchmakingSeconds"], payload["questionSeconds"]) == (30, 20)
    assert payload["questionsPerGame"] == 10
    assert payload["profileChoices"]["defaults"] == {"ride": "monster_truck", "paint": "red"}
    assert {"id": "sports_car", "label": "Sports Car"} in payload["profileChoices"]["rides"]
    assert {"id": "pink", "label": "Pink", "hex": "#ffb4a6"} in payload["profileChoices"]["paints"]


def test_profile_describes_the_vehicle(match):
    assert serializers.profile(match.players["alice"]) == {
        "id": "alice",
        "name": "alice",
        "ride": "sports_car",
        "rideLabel": "Sports Car",
        "paint": "pink",
        "paintLabel": "Pink",
        "paintHex": "#ffb4a6",
        "isBot": False,
    }
    assert serializers.profile(match.players["bot-1"])["isBot"] is True


def test_question_is_numbered_from_one_and_lists_options_in_order(match):
    match.start_next_round()
    payload = serializers.question(match)
    assert (payload["id"], payload["index"], payload["total"], payload["seconds"]) == (7, 1, 2, 20)
    assert [option["key"] for option in payload["options"]] == ["A", "B", "C", "D"]
    assert "correct_option" not in payload and "correctOption" not in payload


def test_race_progress_is_a_share_of_the_finish_score(match):
    match.players["bob"].score = match.finish_score * 2
    standings = serializers.race_standings(match)
    assert standings["finishScore"] == 1800
    progress = {racer["id"]: racer["progressRatio"] for racer in standings["players"]}
    assert progress == {"alice": 0, "bob": 1, "bot-1": 0}


def test_question_result_reveals_the_answer_and_ranks_players(match):
    match.start_next_round()
    match.submit_answer("bob", 7, "B")
    match.submit_answer("alice", 7, "A")
    match.close_round()

    payload = serializers.question_result(match)
    assert (payload["correctOption"], payload["correctAnswer"]) == ("B", "Answer B")
    answers = {answer["playerId"]: answer for answer in payload["answers"]}
    assert answers["bob"]["isCorrect"] and answers["bob"]["pointsEarned"] == 600
    assert answers["alice"]["selectedOption"] == "A" and not answers["alice"]["isCorrect"]
    assert answers["bot-1"]["selectedOption"] is None
    # Ties are broken alphabetically, ignoring case.
    assert [row["id"] for row in payload["leaderboard"]] == ["bob", "alice", "bot-1"]


def test_help_used_carries_only_the_fields_of_its_lifeline(match):
    match.start_next_round()
    alice = match.players["alice"]
    question = match.round.question

    fifty_fifty = match.use_lifeline("alice", Lifeline.FIFTY_FIFTY, 7, random.Random(0))
    payload = serializers.help_used(fifty_fifty)
    assert payload["helpType"] == "fifty_fifty" and len(payload["removedOptions"]) == 2
    assert payload["helps"] == {"fiftyFifty": False, "doubleScore": True, "callFriend": True}

    double = serializers.help_used(LifelineUsed(alice, Lifeline.DOUBLE_SCORE, question))
    assert set(double) == {"helpType", "questionId", "doubleScoreActive", "helps"}

    reply = FriendReply(confidence=55, message="It's B!", answered=True)
    call = serializers.help_used(LifelineUsed(alice, Lifeline.CALL_A_FRIEND, question,
                                              friend_reply=reply))  # fmt: skip
    assert (call["confidence"], call["message"], call["friendAnswered"]) == (55, "It's B!", True)


def test_chat_keeps_its_snake_case_keys_and_marks_own_messages():
    message = ChatMessage(1, "game-1", "alice", "Alice", "hi", "12:30")
    assert serializers.chat_message(message) == {
        "id": 1,
        "game_id": "game-1",
        "user_id": "alice",
        "username": "Alice",
        "content": "hi",
        "timestamp": "12:30",
    }
    assert serializers.chat_history([message], "alice")[0]["is_own"] is True
    assert serializers.chat_history([message], "bob")[0]["is_own"] is False
    assert serializers.unread_count(3) == {"unread_count": 3}
