"""Which matches are running, and which match each human player is in.

A lineup is also held here while its match is being set up (the questions are
being drawn), so its players count as busy before the match exists.
"""

from trivia.domain.match import Match
from trivia.domain.players import Player


class GameRegistry:
    def __init__(self) -> None:
        self._matches: dict[str, Match] = {}
        self._match_id_by_player: dict[str, str] = {}
        self._starting: dict[str, Player] = {}  # humans whose match is being set up

    def __len__(self) -> int:
        return len(self._matches)

    def add(self, match: Match) -> None:
        self._matches[match.id] = match
        for player in match.humans:
            self._match_id_by_player[player.id] = match.id

    def remove(self, match: Match) -> None:
        self._matches.pop(match.id, None)
        for player in match.humans:
            if self._match_id_by_player.get(player.id) == match.id:
                del self._match_id_by_player[player.id]

    def hold(self, lineup: list[Player]) -> None:
        """Reserve a lineup's humans while their match is being set up."""
        for player in lineup:
            if not player.is_bot:
                self._starting[player.id] = player

    def release(self, lineup: list[Player]) -> None:
        for player in lineup:
            if self._starting.get(player.id) is player:
                del self._starting[player.id]

    def starting_player(self, player_id: str) -> Player | None:
        """The held player with this id, if their match is still being set up."""
        return self._starting.get(player_id)

    def get(self, match_id: object) -> Match | None:
        """Look up a match by an id that came from a client (any type)."""
        return self._matches.get(match_id) if isinstance(match_id, str) else None

    def match_for_player(self, player_id: str) -> Match | None:
        match_id = self._match_id_by_player.get(player_id)
        return self._matches.get(match_id) if match_id else None

    def is_playing(self, player_id: str) -> bool:
        return player_id in self._starting or self.match_for_player(player_id) is not None
