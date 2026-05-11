import csv
import sqlite3
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "Question generator" / "questions.csv"
DB_PATH = BASE_DIR / "trivia.db"

# Table schema
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS questions (
    id INTEGER PRIMARY KEY,
    topic TEXT NOT NULL,
    difficulty INTEGER NOT NULL,
    question TEXT NOT NULL,
    option_a TEXT NOT NULL,
    option_b TEXT NOT NULL,
    option_c TEXT NOT NULL,
    option_d TEXT NOT NULL,
    correct_option TEXT NOT NULL
);
"""

INSERT_SQL = """
INSERT INTO questions (id, topic, difficulty, question, option_a, option_b, option_c, option_d, correct_option)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

def convert_csv_to_sqlite():
    if not CSV_PATH.exists():
        raise FileNotFoundError(f"CSV file not found at {CSV_PATH}")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("DROP TABLE IF EXISTS questions")
        cursor.execute(CREATE_TABLE_SQL)

        with CSV_PATH.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            for question_id, row in enumerate(reader, start=1):
                cursor.execute(INSERT_SQL, (
                    question_id,
                    row["topic"],
                    int(row["difficulty"]),
                    row["question"],
                    row["option_a"],
                    row["option_b"],
                    row["option_c"],
                    row["option_d"],
                    row["correct_option"]
                ))

    print(f"Successfully converted {CSV_PATH} to {DB_PATH}")

if __name__ == "__main__":
    convert_csv_to_sqlite()
