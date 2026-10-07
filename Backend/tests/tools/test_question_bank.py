"""The question pipeline's pure helpers. No LLM is called."""

import csv
import importlib

import pytest

from tools.question_bank import csv_store
from tools.question_bank.check_answers import get_wrong_question_ids, parse_model_answers
from tools.question_bank.dedupe_questions import get_ids_to_delete
from tools.question_bank.generate_questions import validate_question
from trivia.config import Settings


def question_row(question_id, question="What?", correct_option="A"):
    return {
        "id": question_id,
        "topic": "Science",
        "difficulty": 3,
        "question": question,
        "option_a": "a",
        "option_b": "b",
        "option_c": "c",
        "option_d": "d",
        "correct_option": correct_option,
    }


@pytest.fixture
def questions_csv(tmp_path):
    path = tmp_path / "questions.csv"
    csv_store.append_questions([question_row(i, f"Question {i}?") for i in range(1, 6)], path)
    return path


def ids_and_questions(path):
    with path.open(newline="", encoding="utf-8") as csv_file:
        return [(row["id"], row["question"]) for row in csv.DictReader(csv_file)]


# csv_store ------------------------------------------------------------------


def test_append_writes_the_header_once(questions_csv):
    csv_store.append_questions([question_row(6, "Question 6?")], questions_csv)
    rows, fieldnames = csv_store.read_questions(questions_csv)
    assert fieldnames == csv_store.QUESTION_FIELDS
    assert [row["id"] for row in rows] == ["1", "2", "3", "4", "5", "6"]


def test_deleting_questions_renumbers_the_rest_in_order(questions_csv):
    assert csv_store.delete_questions([2, 4], questions_csv) == 2
    assert ids_and_questions(questions_csv) == [
        ("1", "Question 1?"),
        ("2", "Question 3?"),
        ("3", "Question 5?"),
    ]


def test_deleting_nothing_leaves_the_file_alone(questions_csv):
    before = questions_csv.read_bytes()
    assert csv_store.delete_questions([], questions_csv) == 0
    assert csv_store.delete_questions([99], questions_csv) == 0
    assert questions_csv.read_bytes() == before


def test_next_question_id_follows_the_highest_id(tmp_path, questions_csv):
    assert csv_store.next_question_id(tmp_path / "missing.csv") == 1
    assert csv_store.next_question_id(questions_csv) == 6


def test_a_csv_without_header_is_rejected(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    with pytest.raises(ValueError, match="CSV header"):
        csv_store.read_questions(empty)


# check_answers --------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw_answer", "expected"),
    [
        ("A\nB\nC", ["A", "B", "C"]),
        ("1. a\n2. d\n3. B", ["A", "D", "B"]),
        ("ABC", ["A", "B", "C"]),  # no separators: every letter counts
    ],
)
def test_parse_model_answers(raw_answer, expected):
    assert parse_model_answers(raw_answer, 3) == expected


def test_parse_model_answers_rejects_the_wrong_number_of_answers():
    with pytest.raises(ValueError, match="Expected 3 answers, got 2"):
        parse_model_answers("A\nB", 3)


def test_questions_the_model_answers_differently_are_marked_wrong(capsys):
    questions = [question_row("1", correct_option="A"), question_row("2", correct_option=" c ")]
    assert get_wrong_question_ids(questions, ["B", "C"]) == [1]
    assert "Deleted question 1" in capsys.readouterr().out


# dedupe_questions -----------------------------------------------------------


def test_dedupe_keeps_the_first_question_of_each_group():
    llm_output = {
        "repetitive_group_A": [7, 3, 9],
        "repetitive_group_B": ["12", "4"],
        "single": [5],
        "not_a_group": "oops",
    }
    assert get_ids_to_delete(llm_output) == [3, 9, 4]


# generate_questions ---------------------------------------------------------


def test_a_generated_question_becomes_a_csv_row():
    raw = {
        "topic": "Science",
        "difficulty": 4,
        "question": "Which planet is red?",
        "options": {"A": "Venus", "B": "Mars", "C": "Earth", "D": "Moon"},
        "correct_option": "B",
    }
    row = validate_question(raw, "Science", question_id=42)
    assert list(row) == csv_store.QUESTION_FIELDS
    assert (row["id"], row["option_b"], row["correct_option"]) == (42, "Mars", "B")

    with pytest.raises(ValueError, match="topic"):
        validate_question(raw, "Music", question_id=42)


def test_the_pipeline_edits_the_csv_the_server_reads(monkeypatch):
    monkeypatch.setenv("QUESTIONS_CSV_PATH", "data/custom_questions.csv")
    try:
        configured = importlib.reload(csv_store).QUESTIONS_CSV_PATH
        assert configured == Settings.from_env().questions_csv_path
        assert configured.name == "custom_questions.csv"
    finally:
        monkeypatch.delenv("QUESTIONS_CSV_PATH")
        importlib.reload(csv_store)
