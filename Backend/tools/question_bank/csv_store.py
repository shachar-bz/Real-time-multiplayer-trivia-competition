"""Read and rewrite data/questions.csv, the source of truth for the question bank.

Every step of the pipeline goes through these helpers. Question ids are kept
dense: deleting questions renumbers the remaining ones 1..n in file order, the
same numbering the game database is built with.
"""

import csv
from pathlib import Path

from trivia.config import DATA_DIR

QUESTIONS_CSV_PATH = DATA_DIR / "questions.csv"
QUESTION_FIELDS = [
    "id",
    "topic",
    "difficulty",
    "question",
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_option",
]


def read_questions(csv_path: Path = QUESTIONS_CSV_PATH) -> tuple[list[dict], list[str]]:
    """Every question row (values are strings) and the CSV header."""
    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        fieldnames = reader.fieldnames

    if not fieldnames:
        raise ValueError(f"{csv_path} does not contain a CSV header.")

    return rows, list(fieldnames)


def write_questions(
    rows: list[dict], fieldnames: list[str], csv_path: Path = QUESTIONS_CSV_PATH
) -> None:
    """Replace the whole file with these rows."""
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def append_questions(rows: list[dict], csv_path: Path = QUESTIONS_CSV_PATH) -> None:
    """Add rows at the end of the file, writing the header if the file is new."""
    is_new_file = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=QUESTION_FIELDS)
        if is_new_file:
            writer.writeheader()
        writer.writerows(rows)


def renumber(rows: list[dict]) -> list[dict]:
    """Give the rows the ids 1..n in their current order."""
    for question_id, row in enumerate(rows, start=1):
        row["id"] = question_id
    return rows


def delete_questions(ids_to_delete: list[int], csv_path: Path = QUESTIONS_CSV_PATH) -> int:
    """Remove the questions with these ids, renumber the rest, and return how many went."""
    if not ids_to_delete:
        return 0

    rows, fieldnames = read_questions(csv_path)
    ids_to_delete_set = {str(question_id) for question_id in ids_to_delete}
    rows_to_keep = [row for row in rows if row.get("id") not in ids_to_delete_set]
    write_questions(renumber(rows_to_keep), fieldnames, csv_path)
    return len(rows) - len(rows_to_keep)


def next_question_id(csv_path: Path = QUESTIONS_CSV_PATH) -> int:
    """The id the next appended question gets: one more than the highest id so far."""
    if not csv_path.exists():
        return 1

    with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
        existing_ids = [
            int(row["id"])
            for row in csv.DictReader(csv_file)
            if row.get("id") and row["id"].isdigit()
        ]

    return max(existing_ids, default=0) + 1
