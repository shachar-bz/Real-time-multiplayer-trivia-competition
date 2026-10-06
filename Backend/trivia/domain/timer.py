"""The countdown for a single question, which phone-a-friend can pause."""

import math
from collections.abc import Callable

Clock = Callable[[], float]  # returns seconds, like time.monotonic


class QuestionTimer:
    def __init__(self, duration_seconds: float, clock: Clock):
        self.duration_seconds = duration_seconds
        self._clock = clock
        self._deadline: float | None = None
        self._remaining_while_paused: float | None = None

    def start(self) -> None:
        self._deadline = self._clock() + self.duration_seconds
        self._remaining_while_paused = None

    @property
    def paused(self) -> bool:
        return self._remaining_while_paused is not None

    def remaining(self) -> float:
        """Seconds left, never negative. Frozen while paused."""
        if self._remaining_while_paused is not None:
            return self._remaining_while_paused
        if self._deadline is None:
            return self.duration_seconds
        return max(0.0, self._deadline - self._clock())

    def seconds_left(self) -> int:
        """Whole seconds left, rounded up: what a player's countdown shows."""
        return max(0, math.ceil(self.remaining()))

    @property
    def expired(self) -> bool:
        return self.remaining() <= 0

    def pause(self) -> bool:
        """Freeze the countdown. Returns False if it was already paused."""
        if self.paused:
            return False
        self._remaining_while_paused = self.remaining()
        self._deadline = None
        return True

    def resume(self) -> bool:
        """Continue the countdown. Returns False if it was not paused."""
        if self._remaining_while_paused is None:
            return False
        self._deadline = self._clock() + self._remaining_while_paused
        self._remaining_while_paused = None
        return True
