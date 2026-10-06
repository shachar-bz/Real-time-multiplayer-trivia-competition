"""Pure game rules.

Nothing in this package does I/O or knows about asyncio, Socket.IO, SQLite or
environment variables. Time and randomness are passed in (a `clock` callable
and a `random.Random`), so every rule can be unit tested deterministically.
"""
