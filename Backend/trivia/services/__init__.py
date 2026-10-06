"""Application services: async orchestration of the domain.

Services decide *when* things happen (countdowns, rounds, bot answers, friend
calls) and report *what* happened through the `GameEvents` port. They never
import socketio, aiohttp or sqlite3 and never build wire payloads.
"""
