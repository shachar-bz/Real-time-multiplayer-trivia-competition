import assert from "node:assert/strict";
import { describe, test } from "node:test";
import { SOUND_EFFECTS, roundResultSound } from "../lib/sounds.js";

describe("sound catalogue", () => {
  test("has a file for every sound the client plays itself", () => {
    for (const name of [
      "click",
      "click_possible_answer",
      "game_countdown",
      "ticking_clock",
      "call_friend",
      "no_answer",
      "correct_answer",
      "wrong_answer",
    ]) {
      assert.match(SOUND_EFFECTS[name], /^\/sounds\/[a-z_]+\.mp3$/, name);
    }
  });
});

describe("roundResultSound", () => {
  const resultWith = (answer) => ({ answers: [{ playerId: "other", selectedOption: "A", isCorrect: true }, answer] });

  test("no answer from this player", () => {
    assert.equal(roundResultSound({ answers: [] }, "me"), "no_answer");
    assert.equal(roundResultSound(resultWith({ playerId: "me", selectedOption: null }), "me"), "no_answer");
  });

  test("right or wrong", () => {
    assert.equal(
      roundResultSound(resultWith({ playerId: "me", selectedOption: "B", isCorrect: true }), "me"),
      "correct_answer"
    );
    assert.equal(
      roundResultSound(resultWith({ playerId: "me", selectedOption: "C", isCorrect: false }), "me"),
      "wrong_answer"
    );
  });
});
