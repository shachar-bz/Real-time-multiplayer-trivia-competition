import random

import pytest

from tests.fakes import make_question
from trivia.domain.bots import (
    BOT_NAME_SUFFIX,
    MAX_BOTS_PER_SOLO_GAME,
    BotBrain,
    DifficultyProfile,
    create_bots,
)
from trivia.domain.lifelines import Lifeline
from trivia.domain.players import MAX_NAME_LENGTH, Player, clean_player_name
from trivia.domain.vehicles import PAINTS, RIDES


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("  Alice  ", "Alice"), ("   ", ""), ("x" * 30, "x" * MAX_NAME_LENGTH), (7, "7")],
)
def test_clean_player_name(raw, expected):
    assert clean_player_name(raw) == expected


def test_humans_start_with_every_lifeline_and_a_valid_vehicle():
    player = Player.human("sid-1", "Alice", ride="sportsCar", paint="nope")
    assert player.lifelines == set(Lifeline)
    assert (player.ride, player.paint) == ("sports_car", "red")
    assert not player.is_bot


def brain(accuracy, min_delay=0.0, max_delay=0.0):
    return BotBrain(DifficultyProfile("test", accuracy, min_delay, max_delay))


def test_bot_brain_with_perfect_accuracy_always_answers_correctly():
    perfect = brain(accuracy=1.0, min_delay=2, max_delay=4)
    rng = random.Random(1)
    for _ in range(50):
        plan = perfect.plan(make_question(correct_option="B"), rng)
        assert plan.option == "B"
        assert 2 <= plan.delay_seconds <= 4


def test_bot_brain_with_zero_accuracy_always_picks_a_wrong_option():
    hopeless = brain(accuracy=0.0)
    question = make_question(correct_option="B")
    options = {hopeless.plan(question, random.Random(seed)).option for seed in range(50)}
    assert options == {"A", "C", "D"}


def test_bot_brain_is_reproducible_with_a_seeded_rng():
    coin_flip = brain(accuracy=0.5, min_delay=1, max_delay=9)
    question = make_question()
    assert coin_flip.plan(question, random.Random(7)) == coin_flip.plan(question, random.Random(7))


def test_create_bots_builds_one_to_three_distinct_lifeline_free_bots():
    profiles = (DifficultyProfile("only", 0.5, 1, 2),)
    for seed in range(30):
        bots = create_bots(random.Random(seed), profiles)
        assert 1 <= len(bots) <= MAX_BOTS_PER_SOLO_GAME
        assert len({bot.name for bot in bots}) == len(bots)
        assert len({bot.id for bot in bots}) == len(bots)
        for bot in bots:
            assert bot.is_bot and bot.brain.profile is profiles[0]
            assert bot.name.endswith(BOT_NAME_SUFFIX)
            assert bot.ride in RIDES and bot.paint in PAINTS
            assert bot.lifelines == set()
