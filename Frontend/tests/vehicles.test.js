import assert from "node:assert/strict";
import { describe, test } from "node:test";
import { PAINT_COLORS, RIDES, normalizeChoiceKey, paintFor, rideFor } from "../lib/vehicles.js";

describe("vehicle catalogue", () => {
  test("ids are unique and already normalised", () => {
    for (const catalogue of [RIDES, PAINT_COLORS]) {
      const ids = catalogue.map((entry) => entry.id);
      assert.equal(new Set(ids).size, ids.length);
      ids.forEach((id) => assert.equal(normalizeChoiceKey(id), id));
    }
  });

  test("every ride's default paint exists", () => {
    const paintIds = PAINT_COLORS.map((paint) => paint.id);
    RIDES.forEach((ride) => assert.ok(paintIds.includes(ride.defaultPaint), ride.id));
  });
});

describe("normalizeChoiceKey", () => {
  test("trims, lowercases and turns underscores into dashes", () => {
    assert.equal(normalizeChoiceKey("  Monster_Truck "), "monster-truck");
    assert.equal(normalizeChoiceKey(null), "");
  });
});

describe("rideFor / paintFor", () => {
  test("find the catalogue entry whatever the spelling", () => {
    assert.equal(rideFor({ ride: "monster_truck" }).id, "monster-truck");
    assert.equal(rideFor({ ride: "SUPERBIKE" }).id, "superbike");
    assert.equal(paintFor({ paint: "Blue" }).id, "blue");
  });

  test("fall back to the first entry for unknown or missing values", () => {
    assert.equal(rideFor({ ride: "spaceship" }), RIDES[0]);
    assert.equal(rideFor(undefined), RIDES[0]);
    assert.equal(paintFor({ paint: "plaid" }), PAINT_COLORS[0]);
    assert.equal(paintFor({}), PAINT_COLORS[0]);
  });
});
