"""Which matches are running, and which match each human player is in."""

from trivia.domain.match import Match


class GameRegistry:
    def __init__(self) -> None:
        self._matches: dict[str, Match] = {}
        self._match_id_by_player: dict[str, str] = {}

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

    def get(self, match_id: object) -> Match | None:
        """Look up a match by an id that came from a client (any type)."""
        return self._matches.get(match_id) if isinstance(match_id, str) else None

    def match_for_player(self, player_id: str) -> Match | None:
        match_id = self._match_id_by_player.get(player_id)
        return self._matches.get(match_id) if match_id else None

    def is_playing(self, player_id: str) -> bool:
        return self.match_for_player(player_id) is not None
