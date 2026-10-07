# Backend

The game server: Python 3.11+, asyncio, aiohttp and python-socketio. It runs
the lobby and every match, owns all game rules, and serves the Socket.IO
protocol described in [docs/PROTOCOL.md](../docs/PROTOCOL.md).

## Run it

```bash
python3 -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # optional; every setting has a default
python server.py          # or: python -m trivia, serves http://localhost:8080
```

`GET /` is a health check. On first start, the question database
(`data/trivia.db`) is built from `data/questions.csv`.

## Test and lint

```bash
pip install -r requirements-dev.txt
pytest                                  # all tests (about 20 s)
pytest tests/contract                   # only the wire-protocol contract
ruff check . && ruff format --check .
```

## Layout

```
server.py                 entrypoint
trivia/
  __init__.py             main(): settings + logging + run
  app.py                  create_app(): the composition root
  config.py               Settings, read from the environment / .env
  domain/                 pure game rules (no asyncio, I/O or env)
    match.py              the Match aggregate: rounds, answers, lifelines, ranking
    timer.py              pausable question timer (injected clock)
    scoring.py            points per answer, race finish line
    lifelines.py          fifty-fifty, double score, call a friend
    players.py            Player, name cleaning, starting lifelines
    bots.py               difficulty profiles, BotBrain, bot roster
    questions.py          Question value object
    vehicles.py           ride and paint catalogue
    chat.py               ChatMessage and message validation
  services/               async orchestration, depends only on domain + ports
    ports.py              QuestionBank, ChatStore, FriendAdvisor, GameEvents
    matchmaking.py        Matchmaker: queue + countdown -> lineup
    game_service.py       GameService: runs matches, answers, lifelines, bots
    chat_service.py       ChatService: membership checks, unread counts
    registry.py           GameRegistry: matches by id, player -> match
  adapters/               port implementations
    sqlite_questions.py   SqliteQuestionBank + building the DB from CSV
    sqlite_chat.py        SqliteChatStore
    openai_friend.py      OpenAIFriendAdvisor (pydantic-ai)
  api/                    the only transport-aware layer
    events.py             ClientEvent / ServerEvent names
    serializers.py        domain -> wire payloads
    publisher.py          GameEvents implemented with Socket.IO emits
    socket_handlers.py    lobby, answer and lifeline handlers
    chat_handlers.py      chat handlers
    sounds.py             sound effects and the /sounds route
    http_routes.py        health check
data/questions.csv        the question set (source of truth)
tools/question_bank/      offline LLM pipeline for the question set
tests/
  unit/                   domain, services, adapters, serializers, app
  contract/               real Socket.IO games vs. the recorded protocol
  tools/                  question pipeline helpers
```

[docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) explains the layers, the
concurrency model and the design decisions.

## Conventions

- Dependencies point inward: `api → services → domain`, and
  `adapters → services/ports.py`. `domain/` imports nothing from the other
  layers.
- Services describe *what happened* through `GameEvents`. Only `api/` builds
  payloads or emits.
- Rule violations the player should see raise `GameRuleError(message)`.
  Requests to ignore return `None`.
- Dependency files list packages without pinned versions.
