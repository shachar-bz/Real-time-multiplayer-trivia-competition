import csv
import os
import sqlite3
from pathlib import Path

# Paths
CSV_PATH = Path("Question generator") / "questions.csv"
DB_PATH = Path("trivia.db")

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

    # Connect to SQLite database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create table
    cursor.execute(CREATE_TABLE_SQL)

    # Read CSV and insert data
    with open(CSV_PATH, "r", newline="", encoding="utf-8") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            cursor.execute(INSERT_SQL, (
                int(row["id"]),
                row["topic"],
                int(row["difficulty"]),
                row["question"],
                row["option_a"],
                row["option_b"],
                row["option_c"],
                row["option_d"],
                row["correct_option"]
            ))

    # Commit and close
    conn.commit()
    conn.close()

    print(f"Successfully converted {CSV_PATH} to {DB_PATH}")

if __name__ == "__main__":
    convert_csv_to_sqlite()