import assert from "node:assert/strict";
import { test } from "node:test";
import { cx } from "../lib/classNames.js";
import { ClientEvent, Lifeline, ServerEvent } from "../lib/protocol.js";

// The wire contract as recorded from the server (Backend contract test baseline).
// Renaming an event here without the server is a protocol break.
const SERVER_EVENTS = [
  "answer_received",
  "chat_history",
  "chat_history_cleared",
  "chat_new_message",
  "chat_unread_update",
  "connected",
  "error_message",
  "game_finished",
  "game_started",
  "help_used",
  "matchmaking_status",
  "player_state",
  "question",
  "question_result",
  "question_timer_paused",
  "question_timer_resumed",
  "race_standings",
  "sound_effect",
];

const CLIENT_EVENTS = [
  "answer",
  "chat_open",
  "chat_request_history",
  "chat_send_message",
  "join_queue",
  "leave_queue",
  "use_help",
];

test("the client handles exactly the events the server emits", () => {
  assert.deepEqual(Object.values(ServerEvent).sort(), SERVER_EVENTS);
});

test("the client emits only events the server handles", () => {
  assert.deepEqual(Object.values(ClientEvent).sort(), CLIENT_EVENTS);
});

test("lifeline ids match the server's help types", () => {
  assert.deepEqual(Object.values(Lifeline).sort(), ["call_a_friend", "double_score", "fifty_fifty"]);
});

test("protocol constants cannot be changed at runtime", () => {
  assert.ok(Object.isFrozen(ServerEvent));
  assert.ok(Object.isFrozen(ClientEvent));
  assert.ok(Object.isFrozen(Lifeline));
});

test("cx joins only the truthy class names", () => {
  assert.equal(cx("lane", false, undefined, "", "current"), "lane current");
  assert.equal(cx(), "");
});
