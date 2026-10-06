import csv
import sqlite3

import pytest

from trivia.adapters.sqlite_questions import (
    SqliteQuestionBank,
    build_question_database,
    count_questions,
)
from trivia.config import Settings
from trivia.domain.questions import OPTION_KEYS
from trivia.services.ports import NotEnoughQuestionsError

FIELDS = ["id", "topic", "difficulty", "question", "option_a", "option_b", "option_c", "option_d",
          "correct_option"]  # fmt: skip


def write_csv(path, count, *, first_id=100):
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDS)
        writer.writeheader()
        for number in range(count):
            writer.writerow({
                "id": first_id + number, "topic": "Sport", "difficulty": str(number % 10 + 1),
                "question": f"Question {number}?", "option_a": "a", "option_b": "b",
                "option_c": "c", "option_d": "d", "correct_option": " b ",
            })  # fmt: skip
    return path


def test_build_renumbers_ids_and_parses_difficulty(tmp_path):
    db_path = tmp_path / "nested" / "trivia.db"
    assert build_question_database(write_csv(tmp_path / "q.csv", 3), db_path) == 3

    with sqlite3.connect(db_path) as connection:
        rows = connection.execute("SELECT id, difficulty FROM questions ORDER BY id").fetchall()
    assert rows == [(1, 1), (2, 2), (3, 3)]


async def test_ensure_seeded_builds_a_missing_database(tmp_path):
    bank = SqliteQuestionBank(tmp_path / "data" / "trivia.db", write_csv(tmp_path / "q.csv", 4))
    await bank.ensure_seeded()
    assert count_questions(bank.db_path) == 4


async def test_ensure_seeded_keeps_an_existing_database(tmp_path):
    db_path = tmp_path / "trivia.db"
    build_question_database(write_csv(tmp_path / "small.csv", 2), db_path)
    bank = SqliteQuestionBank(db_path, write_csv(tmp_path / "big.csv", 9))
    await bank.ensure_seeded()
    assert count_questions(db_path) == 2


async def test_ensure_seeded_needs_a_csv_when_the_database_is_empty(tmp_path):
    with pytest.raises(FileNotFoundError):
        await SqliteQuestionBank(tmp_path / "trivia.db", tmp_path / "missing.csv").ensure_seeded()


async def test_draw_returns_distinct_domain_questions(tmp_path):
    db_path = tmp_path / "trivia.db"
    build_question_database(write_csv(tmp_path / "q.csv", 5), db_path)
    questions = await SqliteQuestionBank(db_path).draw(5)

    assert sorted(question.id for question in questions) == [1, 2, 3, 4, 5]
    assert questions[0].correct_option == "B"  # stripped and upper-cased
    assert questions[0].correct_answer == "b"


async def test_draw_fails_when_the_bank_is_too_small(tmp_path):
    db_path = tmp_path / "trivia.db"
    build_question_database(write_csv(tmp_path / "q.csv", 2), db_path)
    with pytest.raises(NotEnoughQuestionsError, match="Expected at least 3 questions"):
        await SqliteQuestionBank(db_path).draw(3)
    with pytest.raises(NotEnoughQuestionsError):
        await SqliteQuestionBank(tmp_path / "empty.db").draw(1)


async def test_the_shipped_question_csv_is_playable(tmp_path):
    settings = Settings()
    db_path = tmp_path / "trivia.db"
    count = build_question_database(settings.questions_csv_path, db_path)
    assert count >= settings.questions_per_game

    for question in await SqliteQuestionBank(db_path).draw(count):
        assert question.correct_option in OPTION_KEYS
        assert all(question.options[key].strip() for key in OPTION_KEYS)
        assert question.text.strip()
