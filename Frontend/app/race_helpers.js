import { PAINT_COLORS, RIDES } from "./vehicle_options";

export function normalizeChoiceKey(value) {
  return String(value || "")
    .trim()
    .replaceAll("_", "-")
    .toLowerCase();
}

export function rideFor(player) {
  const rideKey = normalizeChoiceKey(player?.ride);
  return RIDES.find((ride) => normalizeChoiceKey(ride.id) === rideKey) || RIDES[0];
}

export function paintFor(player) {
  const paintKey = normalizeChoiceKey(player?.paint);
  return PAINT_COLORS.find((paint) => normalizeChoiceKey(paint.id) === paintKey) || PAINT_COLORS[0];
}

export function progressFor(player, standings) {
  const rawProgress = Number(player?.progressRatio);

  if (Number.isFinite(rawProgress)) {
    return Math.max(0, Math.min(1, rawProgress));
  }

  const finishScore = Math.max(1, Number(standings?.finishScore) || 1);
  return Math.max(0, Math.min(1, (Number(player?.score) || 0) / finishScore));
}

export function playersByScore(standings, fallbackLeaderboard = []) {
  const players =
    standings?.players?.length > 0
      ? standings.players
      : fallbackLeaderboard;

  return [...players].sort((first, second) => {
    const scoreDelta = (Number(second.score) || 0) - (Number(first.score) || 0);

    if (scoreDelta !== 0) {
      return scoreDelta;
    }

    return String(first.name || "").localeCompare(String(second.name || ""));
  });
}

export function cx(...classNames) {
  return classNames.filter(Boolean).join(" ");
}
