"""Real-time multiplayer trivia race: the backend package.

The code is split into layers, and dependencies only point one way:

    api       Socket.IO and HTTP transport. The only layer that knows wire
              payloads, rooms and sounds.
    services  Async orchestration: matchmaking, running a match, chat.
              Talks to the outside world only through the ports in
              services/ports.py.
    domain    Pure game rules: players, questions, scoring, timer, bots and
              the Match aggregate. No asyncio, sockets, SQL or environment.
    adapters  SQLite and OpenAI implementations of the service ports.

    api -> services -> domain        adapters -> services.ports + domain

`trivia.app.create_app` is the composition root that wires them together.
"""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def main() -> None:
    """Run the server (`python server.py` or `python -m trivia`)."""
    from trivia.app import run_server
    from trivia.config import Settings

    settings = Settings.from_env()
    logging.basicConfig(level=settings.log_level, format=LOG_FORMAT)
    run_server(settings)
