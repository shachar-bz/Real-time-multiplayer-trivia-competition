"""How many points an answer is worth.

A correct answer earns between 300 (answered at the buzzer) and 600 points
(answered instantly), scaled by the time left. Double score doubles it; a wrong
or missing answer earns nothing.
"""

MIN_POINTS_FOR_CORRECT_ANSWER = 300
SPEED_BONUS_POINTS = 300
MAX_POINTS_PER_QUESTION = MIN_POINTS_FOR_CORRECT_ANSWER + SPEED_BONUS_POINTS


def points_for_answer(
    *,
    is_correct: bool,
    double_score: bool,
    remaining_seconds: float,
    total_seconds: float,
) -> int:
    if not is_correct:
        return 0

    time_ratio = max(0, min(1, remaining_seconds / total_seconds))
    points = int(MIN_POINTS_FOR_CORRECT_ANSWER + SPEED_BONUS_POINTS * time_ratio)
    return points * 2 if double_score else points


def race_finish_score(questions_per_game: int) -> int:
    """Score at which a racer's car reaches the finish line (100% progress)."""
    return (questions_per_game + 1) * MAX_POINTS_PER_QUESTION
