def base_score_for_answer(selected_option, correct_option, remaining_time, total_time):
    if selected_option != correct_option:
        return 0

    time_ratio = max(0, min(1, remaining_time / total_time))
    return int(300 + (300 * time_ratio))


def apply_score_helps(score, used_double_score):
    if used_double_score:
        return score * 2

    return score


def points_for_answer(selected_option, correct_option, used_double_score, remaining_time, total_time):
    base_score = base_score_for_answer(
        selected_option,
        correct_option,
        remaining_time,
        total_time,
    )
    return apply_score_helps(base_score, used_double_score)
