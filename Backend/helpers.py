def base_score_for_answer(selected_option, correct_option):
    return int(selected_option == correct_option)


def apply_score_helps(score, used_double_score):
    if used_double_score:
        return score * 2

    return score


def points_for_answer(selected_option, correct_option, used_double_score):
    base_score = base_score_for_answer(selected_option, correct_option)
    return apply_score_helps(base_score, used_double_score)
