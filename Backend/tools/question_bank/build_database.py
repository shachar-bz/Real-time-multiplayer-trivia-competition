"""Step 4 of the question pipeline: rebuild the game's question database from the CSV.

The server builds the database by itself when it is missing, but it keeps
using an existing one, so run this after the CSV changed. It writes to the same
database the server reads (TRIVIA_DB_PATH, default data/trivia.db).

    python -m tools.question_bank.build_database
"""

from trivia.adapters.sqlite_questions import build_question_database
from trivia.config import Settings


def build_database() -> None:
    settings = Settings.from_env()
    count = build_question_database(settings.questions_csv_path, settings.question_db_path)
    print(
        f"Successfully converted {settings.questions_csv_path} to {settings.question_db_path} "
        f"({count} questions)"
    )


if __name__ == "__main__":
    build_database()
