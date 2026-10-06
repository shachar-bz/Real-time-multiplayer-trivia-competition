import assert from "node:assert/strict";
import { describe, test } from "node:test";
import { playersByScore, progressFor, sortPlayersByScore } from "../lib/race.js";

describe("progressFor", () => {
  test("uses the server's progressRatio, clamped to the track", () => {
    assert.equal(progressFor({ progressRatio: 0.25, score: 9999 }, { finishScore: 100 }), 0.25);
    assert.equal(progressFor({ progressRatio: 1.7 }), 1);
    assert.equal(progressFor({ progressRatio: -0.2 }), 0);
  });

  test("falls back to score / finishScore", () => {
    assert.equal(progressFor({ score: 1500 }, { finishScore: 6000 }), 0.25);
    assert.equal(progressFor({ score: 9000 }, { finishScore: 6000 }), 1);
  });

  test("never divides by zero or trusts junk", () => {
    assert.equal(progressFor({ score: 0.5 }, { finishScore: 0 }), 0.5);
    assert.equal(progressFor({ score: "lots" }, { finishScore: 100 }), 0);
    assert.equal(progressFor(undefined, undefined), 0);
  });
});

describe("sortPlayersByScore", () => {
  test("highest score first, ties alphabetical", () => {
    const players = [
      { name: "Cleo", score: 600 },
      { name: "bob", score: 1200 },
      { name: "Ann", score: 600 },
    ];
    assert.deepEqual(
      sortPlayersByScore(players).map((player) => player.name),
      ["bob", "Ann", "Cleo"]
    );
  });

  test("returns a copy and treats missing scores as zero", () => {
    const players = [{ name: "Zed" }, { name: "Amy", score: "300" }];
    const sorted = sortPlayersByScore(players);
    assert.notEqual(sorted, players);
    assert.deepEqual(players.map((player) => player.name), ["Zed", "Amy"]);
    assert.deepEqual(sorted.map((player) => player.name), ["Amy", "Zed"]);
  });

  test("an empty or missing list sorts to an empty list", () => {
    assert.deepEqual(sortPlayersByScore(undefined), []);
    assert.deepEqual(sortPlayersByScore([]), []);
  });
});

describe("playersByScore", () => {
  const leaderboard = [{ name: "Leader", score: 10 }];

  test("prefers the race standings", () => {
    const standings = { players: [{ name: "B", score: 1 }, { name: "A", score: 2 }] };
    assert.deepEqual(
      playersByScore(standings, leaderboard).map((player) => player.name),
      ["A", "B"]
    );
  });

  test("falls back to the leaderboard when the standings are empty", () => {
    assert.deepEqual(playersByScore({ players: [] }, leaderboard), leaderboard);
    assert.deepEqual(playersByScore(null, leaderboard), leaderboard);
  });
});
