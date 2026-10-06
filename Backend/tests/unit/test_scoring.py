import pytest

from trivia.domain.scoring import MAX_POINTS_PER_QUESTION, points_for_answer, race_finish_score


def score(*, is_correct=True, double_score=False, remaining=20.0, total=20.0):
    return points_for_answer(
        is_correct=is_correct,
        double_score=double_score,
        remaining_seconds=remaining,
        total_seconds=total,
    )


def test_wrong_answer_scores_nothing_even_with_double_score():
    assert score(is_correct=False, double_score=True) == 0


@pytest.mark.parametrize(
    ("remaining", "expected"),
    [(20, 600), (10, 450), (0, 300), (19.99, 599)],
)
def test_correct_answer_earns_300_plus_a_speed_bonus(remaining, expected):
    assert score(remaining=remaining) == expected


def test_time_ratio_is_clamped():
    assert score(remaining=50) == MAX_POINTS_PER_QUESTION
    assert score(remaining=-5) == 300


def test_double_score_doubles_the_points():
    assert score(remaining=10, double_score=True) == 900


def test_race_finish_score_is_one_question_beyond_the_game():
    assert race_finish_score(10) == 6600
    assert race_finish_score(2) == 1800
