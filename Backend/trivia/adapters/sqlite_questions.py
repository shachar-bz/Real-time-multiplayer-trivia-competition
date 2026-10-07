"""The question bank: an SQLite table built from `data/questions.csv`.

The CSV is the source of truth and lives in git; the database is a build
artefact. `ensure_seeded()` builds it on startup when it is missing or empty,
so a fresh clone runs without any manual step.
"""

import asyncio
import csv
import logging
import sqlite3
from contextlib import closing
from pathlib import Path

from trivia.domain.questions import Question
from trivia.services.ports import NotEnoughQuestionsError

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE questions (
    id INTEGER PRIMARY KEY,
    topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL
)
"""

INSERT_SQL = """
INSERT INTO questions
    (id, topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

DRAW_SQL = """
SELECT id, topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option
FROM questions
ORDER BY RANDOM()
LIMIT ?
"""


def build_question_database(csv_path: Path, db_path: Path) -> int:
    """(Re)create the questions table from the CSV and return the question count.

    Ids are renumbered 1..n in CSV order.
    """
    if not csv_path.exists():
        raise FileNotFoundError(f"Question CSV not found at {csv_path}")

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        rows = [
            (
                question_id,
                row["topic"],
                int(row["difficulty"]),
                row["question"],
                row["option_a"],
                row["option_b"],
                row["option_c"],
                row["option_d"],
                row["correct_option"],
            )
            for question_id, row in enumerate(csv.DictReader(csv_file), start=1)
        ]

    db_path.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(db_path)) as connection, connection:
        connection.execute("DROP TABLE IF EXISTS questions")
        connection.execute(CREATE_TABLE_SQL)
        connection.executemany(INSERT_SQL, rows)

    return len(rows)


def count_questions(db_path: Path) -> int:
    if not db_path.exists():
        return 0
    with closing(sqlite3.connect(db_path)) as connection:
        try:
            return connection.execute("SELECT COUNT(*) FROM questions").fetchone()[0]
        except sqlite3.OperationalError:  # no questions table yet
            return 0


class SqliteQuestionBank:
    def __init__(self, db_path: Path, seed_csv_path: Path | None = None):
        self.db_path = db_path
        self.seed_csv_path = seed_csv_path

    async def ensure_seeded(self) -> None:
        """Build the database from the seed CSV if it has no questions yet."""
        if await asyncio.to_thread(count_questions, self.db_path) > 0:
            return
        if self.seed_csv_path is None:
            raise FileNotFoundError(f"No questions in {self.db_path} and no CSV to build from.")

        count = await asyncio.to_thread(build_question_database, self.seed_csv_path, self.db_path)
        logger.info("Built %s with %d questions from %s", self.db_path, count, self.seed_csv_path)

    async def draw(self, count: int) -> list[Question]:
        return await asyncio.to_thread(self._draw, count)

    def _draw(self, count: int) -> list[Question]:
        with closing(sqlite3.connect(self.db_path)) as connection:
            connection.row_factory = sqlite3.Row
            try:
                rows = connection.execute(DRAW_SQL, (count,)).fetchall()
            except sqlite3.OperationalError:  # the table does not exist
                rows = []

        if len(rows) < count:
            raise NotEnoughQuestionsError(
                f"Expected at least {count} questions in {self.db_path}, found {len(rows)}."
            )
        return [question_from_row(row) for row in rows]


def question_from_row(row: sqlite3.Row) -> Question:
    return Question(
        id=row["id"],
        topic=row["topic"],
        difficulty=row["difficulty"],
        text=row["question"],
        options={
            "A": row["option_a"],
            "B": row["option_b"],
            "C": row["option_c"],
            "D": row["option_d"],
        },
        correct_option=row["correct_option"].strip().upper(),
    )
