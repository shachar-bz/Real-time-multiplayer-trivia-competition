"""Composition root: build the aiohttp + Socket.IO app and wire every layer together.

This is the only module that knows every concrete class. Tests replace the
outside world (questions, chat storage, the phone-a-friend model, randomness,
bot speed) through `create_app`'s keyword arguments.
"""

import logging
import random
import time
from dataclasses import dataclass

import socketio
from aiohttp import web

from trivia.adapters.openai_friend import OpenAIFriendAdvisor
from trivia.adapters.sqlite_chat import SqliteChatStore
from trivia.adapters.sqlite_questions import SqliteQuestionBank
from trivia.api.chat_handlers import register_chat_handlers
from trivia.api.http_routes import register_http_routes
from trivia.api.publisher import SocketIOGameEvents
from trivia.api.socket_handlers import register_socket_handlers
from trivia.api.sounds import register_sound_route
from trivia.config import Settings
from trivia.domain.bots import DEFAULT_PROFILES, DifficultyProfile
from trivia.services.chat_service import ChatService
from trivia.services.game_service import GameService
from trivia.services.matchmaking import Matchmaker
from trivia.services.ports import ChatStore, FriendAdvisor, QuestionBank
from trivia.services.registry import GameRegistry


@dataclass(frozen=True)
class Services:
    """The wired object graph, stored on the app so tests can reach it."""

    settings: Settings
    registry: GameRegistry
    matchmaker: Matchmaker
    games: GameService
    chat: ChatService


SERVICES = web.AppKey("services", Services)


def create_app(
    settings: Settings | None = None,
    *,
    question_bank: QuestionBank | None = None,
    chat_store: ChatStore | None = None,
    friend_advisor: FriendAdvisor | None = None,
    rng: random.Random | None = None,
    bot_profiles: tuple[DifficultyProfile, ...] = DEFAULT_PROFILES,
) -> web.Application:
    settings = settings or Settings.from_env()
    rng = rng or random.Random()
    clock = time.monotonic

    sio = socketio.AsyncServer(
        async_mode="aiohttp", cors_allowed_origins=settings.cors_allowed_origins
    )
    app = web.Application()
    sio.attach(app)

    if question_bank is None:
        sqlite_questions = SqliteQuestionBank(
            settings.question_db_path, seed_csv_path=settings.questions_csv_path
        )

        async def seed_questions(app: web.Application) -> None:
            await sqlite_questions.ensure_seeded()

        app.on_startup.append(seed_questions)
        question_bank = sqlite_questions

    events = SocketIOGameEvents(sio)
    registry = GameRegistry()
    chat = ChatService(
        store=chat_store or SqliteChatStore(settings.chat_db_path),
        registry=registry,
        events=events,
    )
    games = GameService(
        events=events,
        registry=registry,
        question_bank=question_bank,
        friend_advisor=friend_advisor
        or OpenAIFriendAdvisor(settings.openai_api_key, settings.friend_model),
        chat=chat,
        question_seconds=settings.question_seconds,
        questions_per_game=settings.questions_per_game,
        result_seconds=settings.result_seconds,
        friend_timeout_seconds=settings.call_friend_timeout_seconds,
        friend_confidence_range=(
            settings.call_friend_min_confidence,
            settings.call_friend_max_confidence,
        ),
        clock=clock,
        rng=rng,
    )
    matchmaker = Matchmaker(
        events=events,
        registry=registry,
        start_match=games.start_match,
        countdown_seconds=settings.matchmaking_seconds,
        clock=clock,
        rng=rng,
        bot_profiles=bot_profiles,
    )

    register_socket_handlers(sio, settings=settings, matchmaker=matchmaker, game_service=games)
    register_chat_handlers(sio, chat)
    register_http_routes(
        app, matchmaker=matchmaker, registry=registry, question_db_path=settings.question_db_path
    )
    register_sound_route(app, settings.sounds_dir)

    async def stop_background_work(app: web.Application) -> None:
        await matchmaker.shutdown()
        await games.shutdown()

    app.on_cleanup.append(stop_background_work)
    app[SERVICES] = Services(settings, registry, matchmaker, games, chat)
    return app


def run_server(settings: Settings | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    settings = settings or Settings.from_env()
    web.run_app(create_app(settings), host=settings.host, port=settings.port)
