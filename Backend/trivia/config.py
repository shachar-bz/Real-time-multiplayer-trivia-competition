"""Runtime settings: one frozen object instead of constants scattered across modules.

`Settings()` gives the defaults used in development; `Settings.from_env()` reads
overrides from the environment and `Backend/.env`. Tests build Settings directly.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8080
    # "*" or a list of origins. The original server allowed every origin.
    cors_allowed_origins: str | list[str] = "*"

    question_db_path: Path = DATA_DIR / "trivia.db"
    questions_csv_path: Path = DATA_DIR / "questions.csv"
    chat_db_path: Path = DATA_DIR / "chat.db"
    sounds_dir: Path = BACKEND_DIR / "sounds"

    matchmaking_seconds: int = 30
    question_seconds: int = 20
    questions_per_game: int = 10
    result_seconds: float = 3

    call_friend_timeout_seconds: float = 10
    call_friend_min_confidence: int = 30
    call_friend_max_confidence: int = 100
    openai_api_key: str | None = None
    friend_model: str = "gpt-5-nano"

    @classmethod
    def from_env(cls, env_file: Path = BACKEND_DIR / ".env") -> "Settings":
        """Build settings from environment variables (see `.env.example`)."""
        load_dotenv(env_file)
        defaults = cls()
        return cls(
            host=os.getenv("HOST", defaults.host),
            port=int(os.getenv("PORT", defaults.port)),
            cors_allowed_origins=_parse_origins(os.getenv("CORS_ALLOWED_ORIGINS")),
            question_db_path=_path_from_env("TRIVIA_DB_PATH", defaults.question_db_path),
            questions_csv_path=_path_from_env("QUESTIONS_CSV_PATH", defaults.questions_csv_path),
            chat_db_path=_path_from_env("CHAT_DB_PATH", defaults.chat_db_path),
            sounds_dir=_path_from_env("SOUNDS_DIR", defaults.sounds_dir),
            matchmaking_seconds=int(os.getenv("MATCHMAKING_SECONDS", defaults.matchmaking_seconds)),
            question_seconds=int(os.getenv("QUESTION_SECONDS", defaults.question_seconds)),
            questions_per_game=int(os.getenv("QUESTIONS_PER_GAME", defaults.questions_per_game)),
            openai_api_key=os.getenv("OPENAI_API_KEY") or None,
            friend_model=os.getenv("FRIEND_MODEL", defaults.friend_model),
        )


def _parse_origins(value: str | None) -> str | list[str]:
    if not value or value.strip() == "*":
        return "*"
    return [origin.strip() for origin in value.split(",") if origin.strip()]


def _path_from_env(name: str, default: Path) -> Path:
    """Read a path; relative paths are relative to the Backend directory."""
    value = os.getenv(name)
    if not value:
        return default
    path = Path(value)
    return path if path.is_absolute() else BACKEND_DIR / path
