/**
 * Race helpers: how far along the track a racer is and who is in front.
 * Pure functions over the server's `raceStandings` / `leaderboard` payloads.
 */

function scoreOf(player) {
  return Number(player?.score) || 0;
}

/**
 * A racer's position on the track as a ratio from 0 (start) to 1 (finish line).
 * Uses the server's `progressRatio` when present, otherwise score / finishScore.
 */
export function progressFor(player, standings) {
  const rawProgress = Number(player?.progressRatio);

  if (Number.isFinite(rawProgress)) {
    return Math.max(0, Math.min(1, rawProgress));
  }

  const finishScore = Math.max(1, Number(standings?.finishScore) || 1);
  return Math.max(0, Math.min(1, scoreOf(player) / finishScore));
}

/** A sorted copy: highest score first, ties broken alphabetically by name. */
export function sortPlayersByScore(players) {
  return [...(players || [])].sort((first, second) => {
    const scoreDelta = scoreOf(second) - scoreOf(first);

    if (scoreDelta !== 0) {
      return scoreDelta;
    }

    return String(first?.name || "").localeCompare(String(second?.name || ""));
  });
}

/** The standings' racers by score, or the leaderboard's when the standings are empty. */
export function playersByScore(standings, fallbackLeaderboard = []) {
  const players =
    standings?.players?.length > 0
      ? standings.players
      : fallbackLeaderboard;

  return sortPlayersByScore(players);
}
