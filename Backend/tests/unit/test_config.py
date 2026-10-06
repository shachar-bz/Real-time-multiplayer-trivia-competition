import os
import re
from pathlib import Path

from trivia import config
from trivia.config import BACKEND_DIR, Settings

ENV_VARS = [
    "HOST", "PORT", "CORS_ALLOWED_ORIGINS", "LOG_LEVEL", "TRIVIA_DB_PATH", "QUESTIONS_CSV_PATH",
    "CHAT_DB_PATH", "SOUNDS_DIR", "MATCHMAKING_SECONDS", "QUESTION_SECONDS",
    "QUESTIONS_PER_GAME", "OPENAI_API_KEY", "FRIEND_MODEL",
]  # fmt: skip


def settings_from(monkeypatch, tmp_path, **env):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return Settings.from_env(env_file=tmp_path / "no-such.env")


def test_defaults_match_the_original_game(monkeypatch, tmp_path):
    settings = settings_from(monkeypatch, tmp_path)
    assert settings == Settings()
    assert (settings.host, settings.port, settings.cors_allowed_origins) == ("0.0.0.0", 8080, "*")
    assert (settings.matchmaking_seconds, settings.question_seconds) == (30, 20)
    assert (settings.questions_per_game, settings.result_seconds) == (10, 3)
    assert settings.question_db_path == BACKEND_DIR / "data" / "trivia.db"
    assert settings.openai_api_key is None


def test_environment_overrides(monkeypatch, tmp_path):
    settings = settings_from(
        monkeypatch,
        tmp_path,
        PORT="9000",
        CORS_ALLOWED_ORIGINS="http://localhost:8081, https://trivia.example",
        LOG_LEVEL="debug",
        SOUNDS_DIR="Sounds",
        CHAT_DB_PATH=str(tmp_path / "chat.db"),
        MATCHMAKING_SECONDS="5",
        OPENAI_API_KEY="sk-test",
    )
    assert settings.port == 9000
    assert settings.cors_allowed_origins == ["http://localhost:8081", "https://trivia.example"]
    assert settings.log_level == "DEBUG"
    assert settings.sounds_dir == BACKEND_DIR / "Sounds"  # relative to Backend/
    assert settings.chat_db_path == Path(tmp_path / "chat.db")
    assert settings.matchmaking_seconds == 5
    assert settings.openai_api_key == "sk-test"


def test_env_example_documents_every_variable_settings_reads(monkeypatch):
    read = []
    real_getenv = os.getenv

    def recording_getenv(name, default=None):
        read.append(name)
        return real_getenv(name, default)

    monkeypatch.setattr(config, "load_dotenv", lambda env_file: None)
    monkeypatch.setattr(config.os, "getenv", recording_getenv)
    Settings.from_env()

    example = (BACKEND_DIR / ".env.example").read_text()
    documented = set(re.findall(r"^(?:# )?([A-Z_]+)=", example, re.MULTILINE))
    assert read and set(read) <= documented
    assert set(read) == set(ENV_VARS)
