import random

import pytest

from tests.fakes import FakeClock, make_question
from trivia.domain.bots import BotBrain, DifficultyProfile
from trivia.domain.lifelines import Lifeline
from trivia.domain.match import (
    FRIEND_CALL_IN_PROGRESS,
    LIFELINE_ALREADY_USED,
    TIMER_COULD_NOT_PAUSE,
    GameRuleError,
    Match,
)
from trivia.domain.players import Player

QUESTION_SECONDS = 20


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def match(clock):
    players = [Player.human("alice", "Alice"), Player.human("bob", "Bob")]
    questions = [make_question(1, correct_option="C"), make_question(2, correct_option="A")]
    return Match("match-1", players, questions, question_seconds=QUESTION_SECONDS, clock=clock)


@pytest.fixture
def rng():
    return random.Random(0)


def test_rounds_run_through_the_questions_in_order(match):
    first = match.start_next_round()
    second = match.start_next_round()
    assert (first.number, first.question.id) == (1, 1)
    assert (second.number, second.question.id) == (2, 2)
    assert match.start_next_round() is None


def test_correct_answer_is_scored_by_time_left(match, clock):
    match.start_next_round()
    clock.advance(10)
    outcome = match.submit_answer("alice", 1, "C")
    assert outcome.points == 450
    assert match.players["alice"].score == 450


def test_wrong_answer_is_recorded_with_zero_points(match):
    match.start_next_round()
    assert match.submit_answer("bob", 1, "A").points == 0
    assert match.round.answers == {"bob": "A"}


@pytest.mark.parametrize(
    ("question_id", "option"),
    [(2, "C"), ("1", "C"), (1, "E"), (1, "")],
    ids=["other question", "id as string", "unknown option", "no option"],
)
def test_invalid_answers_are_ignored_and_do_not_use_up_the_turn(match, question_id, option):
    match.start_next_round()
    assert match.submit_answer("alice", question_id, option) is None
    assert match.submit_answer("alice", 1, "C") is not None


def test_answers_are_ignored_before_a_round_after_it_closes_and_the_second_time(match):
    assert match.submit_answer("alice", 1, "C") is None
    match.start_next_round()
    assert match.submit_answer("alice", 1, "C") is not None
    assert match.submit_answer("alice", 1, "A") is None
    match.close_round()
    assert match.submit_answer("bob", 1, "C") is None
    assert match.submit_answer("stranger", 1, "C") is None


def test_fifty_fifty_removes_two_wrong_options_which_can_no_longer_be_picked(match, rng):
    match.start_next_round()
    used = match.use_lifeline("alice", Lifeline.FIFTY_FIFTY, 1, rng)
    assert len(used.removed_options) == 2
    assert "C" not in used.removed_options
    assert not match.players["alice"].has_lifeline(Lifeline.FIFTY_FIFTY)

    assert match.submit_answer("alice", 1, used.removed_options[0]) is None
    assert match.submit_answer("alice", 1, "C") is not None


def test_double_score_doubles_this_rounds_points_only(match, clock, rng):
    match.start_next_round()
    match.use_lifeline("alice", Lifeline.DOUBLE_SCORE, 1, rng)
    assert match.submit_answer("alice", 1, "C").points == 1200
    match.close_round()

    match.start_next_round()
    assert match.submit_answer("alice", 2, "A").points == 600


def test_a_lifeline_can_be_used_only_once(match, rng):
    match.start_next_round()
    match.use_lifeline("alice", Lifeline.DOUBLE_SCORE, 1, rng)
    with pytest.raises(GameRuleError, match=LIFELINE_ALREADY_USED):
        match.use_lifeline("alice", Lifeline.DOUBLE_SCORE, 1, rng)


def test_invalid_lifeline_requests_are_ignored_before_rules_are_checked(match, rng):
    match.start_next_round()
    match.use_lifeline("alice", Lifeline.DOUBLE_SCORE, 1, rng)
    # Already used, but for the wrong question: silently ignored, not an error.
    assert match.use_lifeline("alice", Lifeline.DOUBLE_SCORE, 2, rng) is None
    match.submit_answer("bob", 1, "C")
    # Bob already answered: lifelines are ignored for him this round.
    assert match.use_lifeline("bob", Lifeline.FIFTY_FIFTY, 1, rng) is None
    assert match.players["bob"].has_lifeline(Lifeline.FIFTY_FIFTY)


def test_calling_a_friend_pauses_the_timer_until_the_call_ends(match, clock, rng):
    round_ = match.start_next_round()
    clock.advance(5)
    used = match.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1, rng)
    assert used.lifeline is Lifeline.CALL_A_FRIEND
    assert round_.timer.paused and round_.friend_call_in_progress

    clock.advance(8)
    assert match.end_friend_call(round_) is True
    assert round_.timer.remaining() == 15
    assert not round_.friend_call_in_progress


def test_only_one_friend_call_at_a_time(match, rng):
    match.start_next_round()
    match.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1, rng)
    with pytest.raises(GameRuleError, match=FRIEND_CALL_IN_PROGRESS):
        match.use_lifeline("bob", Lifeline.CALL_A_FRIEND, 1, rng)
    assert match.players["bob"].has_lifeline(Lifeline.CALL_A_FRIEND)


def test_friend_call_is_refunded_when_the_timer_cannot_pause(match, rng):
    round_ = match.start_next_round()
    round_.timer.pause()
    with pytest.raises(GameRuleError, match=TIMER_COULD_NOT_PAUSE):
        match.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1, rng)
    assert match.players["alice"].has_lifeline(Lifeline.CALL_A_FRIEND)
    assert not round_.friend_call_in_progress


def test_a_friend_call_that_outlives_its_round_does_not_touch_the_next_round(match, rng):
    first = match.start_next_round()
    match.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1, rng)
    match.close_round()
    assert match.end_friend_call(first) is False

    second = match.start_next_round()
    match.use_lifeline("bob", Lifeline.CALL_A_FRIEND, 2, rng)
    assert match.end_friend_call(first) is False
    assert second.timer.paused


def test_refund_returns_a_lifeline(match, rng):
    match.start_next_round()
    match.use_lifeline("alice", Lifeline.CALL_A_FRIEND, 1, rng)
    match.refund_lifeline("alice", Lifeline.CALL_A_FRIEND)
    assert match.players["alice"].has_lifeline(Lifeline.CALL_A_FRIEND)


def test_disconnected_players_are_not_waited_for(match):
    match.start_next_round()
    match.submit_answer("alice", 1, "C")
    assert not match.all_connected_players_answered()
    assert match.mark_disconnected("bob")
    assert match.all_connected_players_answered()


def test_nobody_connected_never_counts_as_everyone_answered(match):
    match.start_next_round()
    match.mark_disconnected("alice")
    match.mark_disconnected("bob")
    assert not match.all_connected_players_answered()
    assert match.mark_disconnected("stranger") is False


def test_a_match_is_abandoned_once_every_human_disconnected(clock):
    robot = Player.bot("bot-1", "Robo 🤖", "superbike", "blue",
                       BotBrain(DifficultyProfile("test", 1.0, 0, 0)))  # fmt: skip
    players = [Player.human("alice", "Alice"), Player.human("bob", "Bob"), robot]
    match = Match("match-2", players, [make_question()], question_seconds=20, clock=clock)

    match.mark_disconnected("alice")
    assert not match.abandoned
    match.mark_disconnected("bob")
    assert match.abandoned  # the connected bot does not count


def test_leaderboard_breaks_ties_alphabetically_and_winners_share_the_top(clock):
    players = [
        Player.human("1", "carol"),
        Player.human("2", "Bob"),
        Player.human("3", "alice"),
        Player.human("4", "Dave"),
    ]
    for player, score in zip(players, [500, 900, 900, 100]):
        player.score = score
    match = Match("m", players, [make_question()], question_seconds=20, clock=clock)

    assert [player.name for player in match.leaderboard()] == ["alice", "Bob", "carol", "Dave"]
    assert [player.name for player in match.winners()] == ["alice", "Bob"]


def test_round_results_cover_every_player(match, rng):
    match.start_next_round()
    match.use_lifeline("alice", Lifeline.DOUBLE_SCORE, 1, rng)
    match.submit_answer("alice", 1, "C")
    match.close_round()

    alice, bob = match.round_results()
    assert (alice.selected_option, alice.is_correct, alice.double_score_used) == ("C", True, True)
    assert alice.points_earned == 1200
    assert (bob.selected_option, bob.is_correct, bob.points_earned) == (None, False, 0)


def test_a_match_needs_questions(clock):
    with pytest.raises(ValueError):
        Match("m", [], [], question_seconds=20, clock=clock)
