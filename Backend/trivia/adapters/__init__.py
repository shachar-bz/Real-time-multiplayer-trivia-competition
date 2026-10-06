"""Infrastructure adapters: SQLite and OpenAI implementations of the service ports.

Blocking SQLite calls run in a worker thread (`asyncio.to_thread`) so they never
stall the event loop that serves every connected player.
"""
