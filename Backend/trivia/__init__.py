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

