"""Plain HTTP routes: a health check at GET /."""

from pathlib import Path

from aiohttp import web

from trivia.api import serializers
from trivia.services.matchmaking import Matchmaker
from trivia.services.registry import GameRegistry


def register_http_routes(
    app: web.Application,
    *,
    matchmaker: Matchmaker,
    registry: GameRegistry,
    question_db_path: Path,
) -> None:
    async def health(request: web.Request) -> web.Response:
        return web.json_response(
            serializers.health(
                waiting_players=matchmaker.waiting_count,
                active_games=len(registry),
                db_path=question_db_path,
            )
        )

    app.router.add_get("/", health)
