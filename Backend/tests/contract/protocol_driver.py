"""Drive a running trivia server through scripted games and record its wire protocol.

The scenarios are a port of the script that captured `protocol_baseline.json`
from the original server. One difference: before a client acts, it waits until
the server has finished reacting to the previous action (the "settle" waits
below). That keeps the recorded event order independent of event-loop timing,
so the contract test is strict *and* deterministic.

What gets recorded:
- `shapes`: for every server event, the distinct payload shapes (keys + value
  types, see `shape`).
- `sequences`: for every client, the event names it received in order, with
  consecutive repeats of timing-dependent events collapsed (see COLLAPSED_EVENTS).
- `http`: the health route's shape and the status of a static sound file.
"""

import asyncio
import json
from collections import defaultdict
from dataclasses import dataclass, field

import aiohttp
import socketio

# Shortened game timings for the contract run (the baseline used the same values).
MATCHMAKING_SECONDS = 2
QUESTION_SECONDS = 3
QUESTIONS_PER_GAME = 2
RESULT_SECONDS = 0.5
FRIEND_DELAY_SECONDS = 0.3
BOT_DELAY_SECONDS = (0.1, 0.3)

# Every contract question has "C" as its answer, so who scores and who wins does
# not depend on which question the server draws first.
CORRECT_OPTION = "C"
CONTRACT_QUESTIONS = [
    {
        "id": 1,
        "topic": "Science",
        "difficulty": 3,
        "question": "Which planet is known as the Red Planet?",
        "option_a": "Venus",
        "option_b": "Jupiter",
        "option_c": "Mars",
        "option_d": "Saturn",
        "correct_option": CORRECT_OPTION,
    },
    {
        "id": 2,
        "topic": "Geography",
        "difficulty": 2,
        "question": "What is the capital of Japan?",
        "option_a": "Seoul",
        "option_b": "Beijing",
        "option_c": "Tokyo",
        "option_d": "Bangkok",
        "correct_option": CORRECT_OPTION,
    },
]

# How many of these arrive back to back depends on timing (countdown ticks, bot
# answers, ...), so a run of them counts as one entry in a client's sequence.
COLLAPSED_EVENTS = {"matchmaking_status", "race_standings", "sound_effect", "chat_unread_update"}

DEFAULT_WAIT_SECONDS = 10


def shape(value):
    """Type-level shape of a payload: numbers collapse to "number", list items merge."""
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "str"
    if value is None:
        return "null"
    if isinstance(value, dict):
        return {key: shape(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        merged = None
        for item in value:
            merged = merge(merged, shape(item))
        return [] if merged is None else [merged]
    return type(value).__name__


def merge(first, second):
    """Merge two shapes; differing leaf types become "a|b", missing keys "absent"."""
    if first is None:
        return second
    if isinstance(first, dict) and isinstance(second, dict):
        return {
            key: merge(first.get(key, "absent"), second.get(key, "absent"))
            for key in sorted(set(first) | set(second))
        }
    if isinstance(first, list) and isinstance(second, list):
        if not first or not second:
            return first or second
        return [merge(first[0], second[0])]
    if isinstance(first, str) and isinstance(second, str):
        return "|".join(sorted(set(first.split("|")) | set(second.split("|"))))
    return "MIXED"


@dataclass
class ProtocolRecording:
    http: dict = field(default_factory=dict)
    shapes: dict[str, set[str]] = field(default_factory=lambda: defaultdict(set))
    sequences: dict[str, list[str]] = field(default_factory=dict)


class RecordingClient:
    """A Socket.IO client that records every event and lets a scenario wait for one."""

    def __init__(self, label: str, recording: ProtocolRecording):
        self.label = label
        self.recording = recording
        self.sio = socketio.AsyncClient(reconnection=False)
        self.events: list[str] = []
        self.queues: dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)

        @self.sio.on("*")
        async def record_event(event, data=None):
            self.events.append(event)
            recording.shapes[event].add(json.dumps(shape(data), sort_keys=True))
            await self.queues[event].put(data)

    async def connect(self, base_url: str) -> None:
        await self.sio.connect(base_url, transports=["websocket"])
        await self.wait("connected")

    async def emit(self, event: str, data=None) -> None:
        await self.sio.emit(event, data)

    async def disconnect(self) -> None:
        if self.sio.connected:
            await self.sio.disconnect()

    async def wait(self, event: str, *, predicate=None, timeout: float = DEFAULT_WAIT_SECONDS):
        """Consume this client's received `event`s until one matches `predicate`."""
        while True:
            data = await asyncio.wait_for(self.queues[event].get(), timeout)
            if predicate is None or predicate(data):
                return data

    def discard_received(self, event: str) -> None:
        """Forget `event`s received so far, so the next `wait` sees a fresh one."""
        queue = self.queues[event]
        while not queue.empty():
            queue.get_nowait()

    def collapsed_sequence(self) -> list[str]:
        sequence = []
        for event in self.events:
            if sequence and sequence[-1] == event and event in COLLAPSED_EVENTS:
                continue
            sequence.append(event)
        return sequence


def is_sound(name):
    return lambda payload: payload["name"] == name


async def record_protocol(base_url: str) -> ProtocolRecording:
    recording = ProtocolRecording()
    recording.http = await record_http(base_url)
    await multiplayer_scenario(base_url, recording)
    await solo_scenario(base_url, recording)
    return recording


async def record_http(base_url: str) -> dict:
    async with aiohttp.ClientSession() as http:
        async with http.get(f"{base_url}/") as response:
            health = await response.json()
        async with http.get(f"{base_url}/sounds/win_game.mp3") as response:
            sound_status = response.status

    return {"GET /": shape(health), "GET /sounds/win_game.mp3 status": sound_status}


async def multiplayer_scenario(base_url: str, recording: ProtocolRecording) -> None:
    """Four players queue, one leaves; three race with lifelines, chat and a disconnect."""
    alice = RecordingClient("alice", recording)
    bob = RecordingClient("bob", recording)
    carol = RecordingClient("carol_leaves", recording)
    erin = RecordingClient("erin_disconnects", recording)
    clients = (alice, bob, carol, erin)
    for client in clients:
        await client.connect(base_url)

    # Lobby: a nameless join is rejected, Carol leaves the queue before the countdown ends.
    await alice.emit("join_queue", {"name": "  "})
    await alice.wait("error_message")
    await alice.emit("join_queue", {"name": "Alice", "ride": "sportsCar", "paint": "blue"})
    await alice.wait("matchmaking_status")
    await bob.emit("join_queue", {"name": "Bob"})
    await carol.emit("join_queue", {"name": "Carol", "ride": "superbike", "paint": "pink"})
    await erin.emit("join_queue", {"name": "Erin", "ride": "motorcycle", "paint": "white"})
    await carol.wait("matchmaking_status")
    await carol.emit("leave_queue")

    started = await alice.wait("game_started", timeout=MATCHMAKING_SECONDS + DEFAULT_WAIT_SECONDS)
    await bob.wait("game_started")
    await alice.emit("join_queue", {"name": "Alice again"})
    await alice.wait("error_message")  # already in a game
    game_id = started["gameId"]

    # Question 1: every lifeline, a chat message, then everybody answers.
    question = await alice.wait("question")
    await bob.wait("question")
    await erin.wait("question")
    fifty_fifty = {"helpType": "fifty_fifty", "questionId": question["id"]}
    await alice.emit("use_help", fifty_fifty)
    await alice.wait("help_used")
    await alice.emit("use_help", fifty_fifty)
    await alice.wait("error_message")  # lifeline already used
    await bob.emit("use_help", {"helpType": "double_score", "questionId": question["id"]})
    await bob.wait("help_used")
    await bob.emit("use_help", {"helpType": "call_a_friend", "questionId": question["id"]})
    await alice.wait("question_timer_paused")
    await bob.wait("help_used", predicate=lambda payload: payload["helpType"] == "call_a_friend")
    await alice.wait("question_timer_resumed")

    await alice.emit("chat_send_message", {"game_id": game_id, "content": "hello racers"})
    await bob.wait("chat_new_message")
    await bob.wait("sound_effect", predicate=is_sound("chat_message"))  # settle
    await bob.emit("chat_open", {"game_id": game_id})
    await bob.wait("chat_unread_update", predicate=lambda payload: payload["unread_count"] == 0)
    await bob.emit("chat_request_history", {"game_id": game_id})
    await bob.wait("chat_history")

    alice.discard_received("race_standings")
    await alice.emit("answer", {"questionId": "wrong-id", "option": CORRECT_OPTION})  # ignored
    await alice.emit("answer", {"questionId": question["id"], "option": CORRECT_OPTION})
    await alice.wait("answer_received")
    await alice.wait("race_standings")  # settle: Alice's answer is fully broadcast
    await bob.emit("answer", {"questionId": question["id"], "option": "A"})  # wrong, doubled
    await bob.wait("answer_received")
    await alice.wait("race_standings")  # settle: Bob's answer is fully broadcast
    await erin.emit("answer", {"questionId": question["id"], "option": "D"})  # wrong
    await alice.wait("question_result")

    # Question 2: Erin disconnects, Bob never answers, so the round times out.
    question = await alice.wait("question")
    await erin.wait("question")
    alice.discard_received("race_standings")
    await erin.disconnect()
    await alice.wait("race_standings")  # settle: Erin's disconnect is broadcast
    await alice.emit("answer", {"questionId": question["id"], "option": CORRECT_OPTION})
    await alice.wait("answer_received")
    await alice.wait("question_result", timeout=QUESTION_SECONDS + DEFAULT_WAIT_SECONDS)

    await alice.wait("game_finished")
    await bob.wait("game_finished")
    await alice.wait("chat_history_cleared")
    await bob.wait("chat_history_cleared")
    await asyncio.sleep(0.3)  # anything emitted after the game would show up in the sequences

    for client in clients:
        recording.sequences[f"multiplayer:{client.label}"] = client.collapsed_sequence()
        await client.disconnect()


async def solo_scenario(base_url: str, recording: ProtocolRecording) -> None:
    """A single player gets bots; the (fast, always-correct) bots answer first and win."""
    dana = RecordingClient("dana", recording)
    await dana.connect(base_url)
    await dana.emit("join_queue", {"name": "Dana", "ride": "monster_truck", "paint": "yellow"})
    started = await dana.wait("game_started", timeout=MATCHMAKING_SECONDS + DEFAULT_WAIT_SECONDS)
    assert any(profile["isBot"] for profile in started["playerProfiles"]), "expected bots"

    for _ in range(QUESTIONS_PER_GAME):
        question = await dana.wait("question")
        await asyncio.sleep(BOT_DELAY_SECONDS[1] + 0.3)  # let every bot answer first
        await dana.emit("answer", {"questionId": question["id"], "option": CORRECT_OPTION})
        await dana.wait("question_result")

    await dana.wait("game_finished")
    await dana.wait("chat_history_cleared")
    await asyncio.sleep(0.3)

    recording.sequences["solo:dana"] = dana.collapsed_sequence()
    await dana.disconnect()
