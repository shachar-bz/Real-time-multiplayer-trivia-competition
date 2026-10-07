import assert from "node:assert/strict";
import { describe, test } from "node:test";
import {
  ActionType,
  EMPTY_RACE_STANDINGS,
  FriendPopupKind,
  Phase,
  canChooseAnswer,
  canUseHelp,
  gameReducer,
  initialState,
  secondsUntil,
  selectRaceStandings,
} from "../lib/gameReducer.js";
import { Lifeline, ServerEvent } from "../lib/protocol.js";

const SELF_ID = "sid-self";
const NOW = 1_000_000;

const CLOSED_POPUP = {
  open: false,
  loading: false,
  message: "",
  confidence: null,
  friendAnswered: null,
  kind: "",
};

/** Freezes a state tree so any accidental mutation inside the reducer throws. */
function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    Object.values(value).forEach(deepFreeze);
  }
  return value;
}

/** Applies actions in order, the way React would, on frozen states. */
function reduce(state, ...actions) {
  return actions.reduce(
    (current, action) => gameReducer(deepFreeze(current), action),
    structuredClone(state)
  );
}

function server(type, payload, extras = {}) {
  return { type, payload, selfId: SELF_ID, now: NOW, ...extras };
}

function standings(...scores) {
  return {
    finishScore: 6600,
    players: scores.map((score, index) => ({
      id: `p${index}`,
      name: `Player ${index}`,
      score,
      progressRatio: score / 6600,
      ride: "motorcycle",
      paint: "blue",
    })),
  };
}

const QUESTION = {
  id: 7,
  index: 2,
  total: 10,
  text: "Which planet is known as the Red Planet?",
  topic: "Space",
  difficulty: 1,
  seconds: 20,
  options: [
    { key: "A", text: "Venus" },
    { key: "B", text: "Mars" },
    { key: "C", text: "Jupiter" },
    { key: "D", text: "Saturn" },
  ],
};

const GAME_INFO = {
  gameId: "game-1",
  players: ["Alice", "Bob"],
  playerProfiles: [],
  questionCount: 10,
  questionSeconds: 20,
  raceStandings: standings(0, 0),
};

/** A state in the middle of a question, with everything a reset should clear. */
function midGameState(overrides = {}) {
  return {
    ...initialState,
    phase: Phase.GAME,
    currentPlayerId: SELF_ID,
    gameInfo: GAME_INFO,
    question: QUESTION,
    selectedOption: "B",
    lockedAnswer: true,
    removedOptions: ["A", "C"],
    doubleScoreActive: true,
    helps: { fiftyFifty: false, doubleScore: false, callFriend: false },
    friendPopup: {
      open: true,
      loading: false,
      message: "It is B.",
      confidence: 80,
      friendAnswered: true,
      kind: FriendPopupKind.RESULT,
    },
    timeLeft: 12,
    questionEndsAt: NOW + 12_000,
    result: { questionId: 6, answers: [] },
    leaderboard: [{ id: "p0", name: "Player 0", score: 600 }],
    raceStandings: standings(900, 300),
    previousRaceStandings: standings(0, 0),
    settledRaceStandings: standings(600, 300),
    errorMessage: "Something went wrong.",
    chatOpen: true,
    chatMessages: [{ id: 1, content: "hi" }],
    chatInput: "draft",
    chatUnreadCount: 3,
    ...overrides,
  };
}

describe("initial state", () => {
  test("starts on the welcome screen with the default timings", () => {
    assert.equal(initialState.phase, Phase.INTRO);
    assert.equal(initialState.connectionStatus, "Disconnected");
    assert.deepEqual(initialState.config, {
      matchmakingSeconds: 30,
      questionSeconds: 20,
      questionsPerGame: 10,
    });
    assert.deepEqual(initialState.waiting, {
      secondsLeft: 30,
      playerCount: 0,
      players: [],
      playerProfiles: [],
    });
    assert.equal(initialState.timeLeft, 20);
    assert.equal(initialState.questionEndsAt, null);
    assert.deepEqual(initialState.helps, { fiftyFifty: true, doubleScore: true, callFriend: true });
    assert.deepEqual(initialState.friendPopup, CLOSED_POPUP);
    assert.equal(initialState.raceStandings, EMPTY_RACE_STANDINGS);
    assert.equal(initialState.previousRaceStandings, EMPTY_RACE_STANDINGS);
    assert.equal(initialState.settledRaceStandings, EMPTY_RACE_STANDINGS);
  });

  test("unknown actions return the same state object", () => {
    const state = midGameState();
    assert.equal(gameReducer(state, { type: "nothing/happened" }), state);
  });
});

describe("socket lifecycle and clock", () => {
  test("connecting stores the socket id as the current player", () => {
    const state = reduce(initialState, { type: ActionType.SOCKET_CONNECTED, socketId: "abc" });
    assert.equal(state.connectionStatus, "Connected");
    assert.equal(state.currentPlayerId, "abc");
  });

  test("disconnecting only changes the status", () => {
    const before = midGameState({ connectionStatus: "Connected" });
    const state = reduce(before, { type: ActionType.SOCKET_DISCONNECTED });
    assert.deepEqual(state, { ...before, connectionStatus: "Disconnected" });
  });

  test("a clock tick sets the seconds left", () => {
    const state = reduce(midGameState(), { type: ActionType.CLOCK_TICKED, secondsLeft: 9 });
    assert.equal(state.timeLeft, 9);
  });

  test("a clock tick within the same second returns the same state object", () => {
    const state = midGameState({ timeLeft: 9 });
    assert.equal(gameReducer(state, { type: ActionType.CLOCK_TICKED, secondsLeft: 9 }), state);
  });
});

describe("server events", () => {
  test("connected: takes the player id and timings from the server", () => {
    const state = reduce(
      initialState,
      server(ServerEvent.CONNECTED, {
        sid: "server-sid",
        matchmakingSeconds: 5,
        questionSeconds: 8,
        questionsPerGame: 3,
        profileChoices: { rides: [], paints: [], defaults: {} },
      })
    );
    assert.equal(state.currentPlayerId, "server-sid");
    assert.deepEqual(state.config, { matchmakingSeconds: 5, questionSeconds: 8, questionsPerGame: 3 });
  });

  test("matchmaking_status: shows the lobby with the server's status", () => {
    const status = { secondsLeft: 12, playerCount: 2, players: ["A", "B"], playerProfiles: [] };
    const state = reduce(initialState, server(ServerEvent.MATCHMAKING_STATUS, status));
    assert.equal(state.phase, Phase.WAITING);
    assert.deepEqual(state.waiting, status);
  });

  test("game_started: resets the previous game and starts every standing at the grid", () => {
    const state = reduce(midGameState(), server(ServerEvent.GAME_STARTED, GAME_INFO));

    assert.equal(state.phase, Phase.GAME);
    assert.deepEqual(state.gameInfo, GAME_INFO);
    assert.deepEqual(state.leaderboard, []);
    assert.deepEqual(state.raceStandings, GAME_INFO.raceStandings);
    assert.deepEqual(state.previousRaceStandings, GAME_INFO.raceStandings);
    assert.deepEqual(state.settledRaceStandings, GAME_INFO.raceStandings);
    assert.equal(state.result, null);
    assert.equal(state.errorMessage, "");
    assert.equal(state.chatOpen, false);
    assert.deepEqual(state.chatMessages, []);
    assert.equal(state.chatInput, "");
    assert.equal(state.chatUnreadCount, 0);
    assert.deepEqual(state.helps, { fiftyFifty: true, doubleScore: true, callFriend: true });
    assert.deepEqual(state.friendPopup, CLOSED_POPUP);
  });

  test("game_started: leaves question state for the next question event to reset", () => {
    const before = midGameState();
    const state = reduce(before, server(ServerEvent.GAME_STARTED, GAME_INFO));
    assert.deepEqual(state.question, before.question);
    assert.equal(state.selectedOption, "B");
    assert.equal(state.lockedAnswer, true);
    assert.deepEqual(state.removedOptions, ["A", "C"]);
    assert.equal(state.doubleScoreActive, true);
    assert.equal(state.timeLeft, 12);
    assert.equal(state.questionEndsAt, before.questionEndsAt);
  });

  test("game_started: missing race standings fall back to an empty race", () => {
    const state = reduce(
      midGameState(),
      server(ServerEvent.GAME_STARTED, { ...GAME_INFO, raceStandings: undefined })
    );
    assert.deepEqual(state.raceStandings, EMPTY_RACE_STANDINGS);
    assert.deepEqual(state.previousRaceStandings, EMPTY_RACE_STANDINGS);
    assert.deepEqual(state.settledRaceStandings, EMPTY_RACE_STANDINGS);
  });

  test("player_state: replaces the lifelines", () => {
    const helps = { fiftyFifty: true, doubleScore: false, callFriend: true };
    const state = reduce(midGameState(), server(ServerEvent.PLAYER_STATE, { helps, profile: {} }));
    assert.deepEqual(state.helps, helps);
  });

  test("question: resets the round and starts the clock from `now`", () => {
    const next = { ...QUESTION, id: 8, index: 3, seconds: 15 };
    const state = reduce(
      midGameState({ phase: Phase.RESULT }),
      server(ServerEvent.QUESTION, next, { now: 5_000 })
    );

    assert.equal(state.phase, Phase.GAME);
    assert.deepEqual(state.question, next);
    assert.equal(state.selectedOption, null);
    assert.equal(state.lockedAnswer, false);
    assert.deepEqual(state.removedOptions, []);
    assert.equal(state.doubleScoreActive, false);
    assert.deepEqual(state.friendPopup, CLOSED_POPUP);
    assert.equal(state.result, null);
    assert.equal(state.timeLeft, 15);
    assert.equal(state.questionEndsAt, 5_000 + 15_000);
  });

  test("question: keeps lifelines, standings, errors and chat", () => {
    const before = midGameState();
    const state = reduce(before, server(ServerEvent.QUESTION, QUESTION));
    assert.deepEqual(state.helps, before.helps);
    assert.deepEqual(state.raceStandings, before.raceStandings);
    assert.equal(state.errorMessage, before.errorMessage);
    assert.deepEqual(state.chatMessages, before.chatMessages);
  });

  test("answer_received: locks in the option the server accepted", () => {
    const state = reduce(
      midGameState({ selectedOption: null, lockedAnswer: false }),
      server(ServerEvent.ANSWER_RECEIVED, { questionId: 7, selectedOption: "D" })
    );
    assert.equal(state.selectedOption, "D");
    assert.equal(state.lockedAnswer, true);
  });

  test("sound_effect: changes nothing", () => {
    const before = midGameState();
    const sound = { name: "submit_answer", url: "/sounds/submit_answer.mp3" };
    assert.equal(gameReducer(before, server(ServerEvent.SOUND_EFFECT, sound)), before);
  });

  test("chat_new_message: appends and marks our own messages by socket id", () => {
    const base = { id: 2, game_id: "game-1", username: "Me", content: "go", timestamp: "10:00" };
    const state = reduce(
      midGameState(),
      server(ServerEvent.CHAT_NEW_MESSAGE, { ...base, user_id: SELF_ID }),
      server(ServerEvent.CHAT_NEW_MESSAGE, { ...base, id: 3, user_id: "someone-else" })
    );
    assert.equal(state.chatMessages.length, 3);
    assert.deepEqual(state.chatMessages[1], { ...base, user_id: SELF_ID, is_own: true });
    assert.equal(state.chatMessages[2].is_own, false);
  });

  test("chat_new_message: an explicit is_own from the server wins", () => {
    const state = reduce(
      midGameState({ chatMessages: [] }),
      server(ServerEvent.CHAT_NEW_MESSAGE, { id: 4, user_id: SELF_ID, is_own: false })
    );
    assert.equal(state.chatMessages[0].is_own, false);
  });

  test("chat_history: replaces the messages", () => {
    const history = [{ id: 9, username: "Bob", content: "hey", timestamp: "10:01", is_own: false }];
    const state = reduce(midGameState(), server(ServerEvent.CHAT_HISTORY, history));
    assert.deepEqual(state.chatMessages, history);
  });

  test("chat_unread_update: stores the count, defaulting to zero", () => {
    let state = reduce(midGameState(), server(ServerEvent.CHAT_UNREAD_UPDATE, { unread_count: 5 }));
    assert.equal(state.chatUnreadCount, 5);
    state = reduce(state, server(ServerEvent.CHAT_UNREAD_UPDATE, {}));
    assert.equal(state.chatUnreadCount, 0);
  });

  test("chat_history_cleared: empties messages and the unread badge", () => {
    const state = reduce(midGameState(), server(ServerEvent.CHAT_HISTORY_CLEARED, {}));
    assert.deepEqual(state.chatMessages, []);
    assert.equal(state.chatUnreadCount, 0);
    assert.equal(state.chatOpen, true);
  });

  test("race_standings: updates only the live standings", () => {
    const before = midGameState();
    const live = standings(1200, 300);
    const state = reduce(before, server(ServerEvent.RACE_STANDINGS, live));
    assert.deepEqual(state.raceStandings, live);
    assert.deepEqual(state.previousRaceStandings, before.previousRaceStandings);
    assert.deepEqual(state.settledRaceStandings, before.settledRaceStandings);
  });

  test("race_standings: a null payload means an empty race", () => {
    const state = reduce(midGameState(), server(ServerEvent.RACE_STANDINGS, null));
    assert.deepEqual(state.raceStandings, EMPTY_RACE_STANDINGS);
  });

  test("question_result: animates from the last settled standings, not the live ones", () => {
    const before = midGameState();
    const roundStandings = standings(1500, 300);
    const questionResult = {
      questionId: 7,
      correctOption: "B",
      correctAnswer: "Mars",
      answers: [],
      leaderboard: [{ id: "p0", name: "Player 0", score: 1500 }],
      raceStandings: roundStandings,
    };
    const state = reduce(before, server(ServerEvent.QUESTION_RESULT, questionResult));

    assert.equal(state.phase, Phase.RESULT);
    assert.deepEqual(state.result, questionResult);
    assert.deepEqual(state.leaderboard, questionResult.leaderboard);
    assert.deepEqual(state.previousRaceStandings, before.settledRaceStandings);
    assert.deepEqual(state.raceStandings, roundStandings);
    assert.deepEqual(state.settledRaceStandings, roundStandings);
    assert.equal(state.questionEndsAt, null);
    assert.equal(state.timeLeft, 0);
  });

  test("question_result: each round animates from the previous round's result", () => {
    const first = standings(600, 0);
    const second = standings(1200, 600);
    const resultWith = (raceStandings) => ({ answers: [], leaderboard: [], raceStandings });
    const state = reduce(
      initialState,
      server(ServerEvent.GAME_STARTED, GAME_INFO),
      server(ServerEvent.QUESTION, QUESTION),
      server(ServerEvent.RACE_STANDINGS, standings(300, 0)),
      server(ServerEvent.QUESTION_RESULT, resultWith(first)),
      server(ServerEvent.QUESTION, QUESTION),
      server(ServerEvent.RACE_STANDINGS, standings(900, 0)),
      server(ServerEvent.QUESTION_RESULT, resultWith(second))
    );
    assert.deepEqual(state.previousRaceStandings, first);
    assert.deepEqual(state.raceStandings, second);
  });

  test("question_result: missing standings fall back to an empty race", () => {
    const state = reduce(
      midGameState(),
      server(ServerEvent.QUESTION_RESULT, { answers: [], leaderboard: [] })
    );
    assert.deepEqual(state.raceStandings, EMPTY_RACE_STANDINGS);
    assert.deepEqual(state.settledRaceStandings, EMPTY_RACE_STANDINGS);
  });

  describe("help_used", () => {
    const helps = { fiftyFifty: false, doubleScore: true, callFriend: true };
    const fresh = () =>
      midGameState({
        removedOptions: [],
        doubleScoreActive: false,
        friendPopup: CLOSED_POPUP,
        lockedAnswer: false,
      });

    test("fifty_fifty removes the two options", () => {
      const state = reduce(
        fresh(),
        server(ServerEvent.HELP_USED, {
          questionId: 7,
          helpType: Lifeline.FIFTY_FIFTY,
          helps,
          removedOptions: ["A", "D"],
        })
      );
      assert.deepEqual(state.helps, helps);
      assert.deepEqual(state.removedOptions, ["A", "D"]);
      assert.equal(state.doubleScoreActive, false);
      assert.deepEqual(state.friendPopup, CLOSED_POPUP);
    });

    test("double_score arms the multiplier", () => {
      const state = reduce(
        fresh(),
        server(ServerEvent.HELP_USED, {
          questionId: 7,
          helpType: Lifeline.DOUBLE_SCORE,
          helps,
          doubleScoreActive: 1,
        })
      );
      assert.equal(state.doubleScoreActive, true);
      assert.deepEqual(state.removedOptions, []);
    });

    test("call_a_friend shows the friend's answer", () => {
      const state = reduce(
        fresh(),
        server(ServerEvent.HELP_USED, {
          questionId: 7,
          helpType: Lifeline.CALL_A_FRIEND,
          helps,
          message: "I think it is B.",
          confidence: 72,
          friendAnswered: true,
        })
      );
      assert.deepEqual(state.friendPopup, {
        open: true,
        loading: false,
        message: "I think it is B.",
        confidence: 72,
        friendAnswered: true,
        kind: FriendPopupKind.RESULT,
      });
    });

    test("an unknown help type still updates the lifelines", () => {
      const before = fresh();
      const state = reduce(before, server(ServerEvent.HELP_USED, { helpType: "other", helps }));
      assert.deepEqual(state, { ...before, helps });
    });
  });

  describe("question_timer_paused", () => {
    const pause = (callerId) => ({
      questionId: 7,
      secondsLeft: 11,
      callerId,
      callerName: "Someone",
      message: "someone is calling his friend",
    });

    test("the caller sees their own call ringing", () => {
      const state = reduce(midGameState(), server(ServerEvent.QUESTION_TIMER_PAUSED, pause(SELF_ID)));
      assert.equal(state.timeLeft, 11);
      assert.equal(state.questionEndsAt, null);
      assert.deepEqual(state.friendPopup, {
        open: true,
        loading: true,
        message: "Calling your funniest friend...",
        confidence: null,
        friendAnswered: null,
        kind: FriendPopupKind.CALLER_LOADING,
      });
    });

    test("everyone else waits for the caller", () => {
      const state = reduce(midGameState(), server(ServerEvent.QUESTION_TIMER_PAUSED, pause("other")));
      assert.equal(state.timeLeft, 11);
      assert.equal(state.questionEndsAt, null);
      assert.deepEqual(state.friendPopup, {
        open: true,
        loading: true,
        message: "Someone is calling his friend.",
        confidence: null,
        friendAnswered: null,
        kind: FriendPopupKind.OBSERVER_WAITING,
      });
    });
  });

  describe("question_timer_resumed", () => {
    const resume = server(ServerEvent.QUESTION_TIMER_RESUMED, { questionId: 7, secondsLeft: 11 }, { now: 50_000 });

    for (const kind of [FriendPopupKind.CALLER_LOADING, FriendPopupKind.OBSERVER_WAITING]) {
      test(`closes the ${kind} popup and restarts the clock`, () => {
        const state = reduce(
          midGameState({ friendPopup: { ...CLOSED_POPUP, open: true, loading: true, kind } }),
          resume
        );
        assert.deepEqual(state.friendPopup, CLOSED_POPUP);
        assert.equal(state.timeLeft, 11);
        assert.equal(state.questionEndsAt, 50_000 + 11_000);
      });
    }

    test("keeps the friend's answer on screen", () => {
      const before = midGameState();
      const state = reduce(before, resume);
      assert.deepEqual(state.friendPopup, before.friendPopup);
      assert.equal(state.questionEndsAt, 61_000);
    });
  });

  test("game_finished: shows the final board and clears the game", () => {
    const before = midGameState();
    const finalStandings = standings(6600, 1200);
    const summary = {
      questionCount: 10,
      leaderboard: [{ id: "p0", name: "Player 0", score: 6600 }],
      raceStandings: finalStandings,
    };
    const state = reduce(before, server(ServerEvent.GAME_FINISHED, summary));

    assert.equal(state.phase, Phase.FINISHED);
    assert.deepEqual(state.leaderboard, summary.leaderboard);
    assert.deepEqual(state.previousRaceStandings, before.settledRaceStandings);
    assert.deepEqual(state.raceStandings, finalStandings);
    assert.deepEqual(state.settledRaceStandings, finalStandings);
    assert.equal(state.question, null);
    assert.equal(state.result, null);
    assert.equal(state.gameInfo, null);
    assert.equal(state.questionEndsAt, null);
    assert.equal(state.chatOpen, false);
    assert.deepEqual(state.chatMessages, []);
    assert.equal(state.chatInput, "");
    assert.equal(state.chatUnreadCount, 0);
    assert.deepEqual(state.friendPopup, CLOSED_POPUP);
    // Not reset by game_finished:
    assert.equal(state.timeLeft, before.timeLeft);
    assert.deepEqual(state.helps, before.helps);
    assert.equal(state.errorMessage, before.errorMessage);
  });

  describe("error_message", () => {
    const error = server(ServerEvent.ERROR_MESSAGE, { message: "You already used that help." });

    test("shows the message and closes a popup that is still loading", () => {
      const state = reduce(
        midGameState({ friendPopup: { ...CLOSED_POPUP, open: true, loading: true, kind: "caller_loading" } }),
        error
      );
      assert.equal(state.errorMessage, "You already used that help.");
      assert.deepEqual(state.friendPopup, CLOSED_POPUP);
    });

    test("keeps a popup that already shows an answer", () => {
      const before = midGameState();
      const state = reduce(before, error);
      assert.equal(state.errorMessage, "You already used that help.");
      assert.deepEqual(state.friendPopup, before.friendPopup);
      assert.equal(state.phase, before.phase);
    });

    test("in the lobby, returns to the welcome screen with the message and an empty lobby", () => {
      const state = reduce(
        {
          ...initialState,
          phase: Phase.WAITING,
          waiting: { secondsLeft: 0, playerCount: 2, players: ["A", "B"], playerProfiles: [{}, {}] },
        },
        server(ServerEvent.ERROR_MESSAGE, { message: "The game could not start. Please try again." })
      );
      assert.equal(state.phase, Phase.INTRO);
      assert.equal(state.errorMessage, "The game could not start. Please try again.");
      assert.deepEqual(state.waiting, { secondsLeft: 30, playerCount: 0, players: [], playerProfiles: [] });
    });
  });
});

describe("player actions", () => {
  test("typing a name stores it untrimmed", () => {
    const state = reduce(initialState, { type: ActionType.PLAYER_NAME_CHANGED, name: " Ada " });
    assert.equal(state.playerName, " Ada ");
  });

  test("joining the queue shows the lobby with only us, before the server answers", () => {
    const state = reduce(
      { ...initialState, playerName: "  Ada  ", errorMessage: "old", config: { ...initialState.config, matchmakingSeconds: 7 } },
      { type: ActionType.QUEUE_JOINED, profile: { ride: "superbike", paint: "red" }, socketId: "sock-1" }
    );
    assert.equal(state.phase, Phase.WAITING);
    assert.equal(state.errorMessage, "");
    assert.deepEqual(state.waiting, {
      secondsLeft: 7,
      playerCount: 1,
      players: ["Ada"],
      playerProfiles: [{ id: "sock-1", name: "Ada", ride: "superbike", paint: "red" }],
    });
  });

  test("joining the queue falls back to the known player id, then a placeholder", () => {
    const join = { type: ActionType.QUEUE_JOINED, profile: {}, socketId: undefined };
    const known = reduce({ ...initialState, currentPlayerId: "known" }, join);
    assert.equal(known.waiting.playerProfiles[0].id, "known");
    const unknown = reduce(initialState, { ...join, profile: undefined });
    assert.equal(unknown.waiting.playerProfiles[0].id, "current-player");
  });

  test("leaving the lobby returns to the welcome screen with an empty lobby", () => {
    const state = reduce(
      {
        ...initialState,
        phase: Phase.WAITING,
        errorMessage: "x",
        waiting: { secondsLeft: 3, playerCount: 2, players: ["A", "B"], playerProfiles: [{}] },
      },
      { type: ActionType.LOBBY_LEFT }
    );
    assert.equal(state.phase, Phase.INTRO);
    assert.equal(state.errorMessage, "");
    assert.deepEqual(state.waiting, { secondsLeft: 30, playerCount: 0, players: [], playerProfiles: [] });
  });

  test("choosing an answer locks it immediately", () => {
    const state = reduce(
      midGameState({ selectedOption: null, lockedAnswer: false }),
      { type: ActionType.ANSWER_CHOSEN, option: "C" }
    );
    assert.equal(state.selectedOption, "C");
    assert.equal(state.lockedAnswer, true);
  });

  test("calling a friend opens the ringing popup right away", () => {
    const state = reduce(
      midGameState({ friendPopup: CLOSED_POPUP }),
      { type: ActionType.HELP_REQUESTED, helpType: Lifeline.CALL_A_FRIEND }
    );
    assert.equal(state.errorMessage, "");
    assert.equal(state.friendPopup.kind, FriendPopupKind.CALLER_LOADING);
    assert.equal(state.friendPopup.loading, true);
  });

  test("other lifelines only clear the error", () => {
    const before = midGameState();
    const state = reduce(before, { type: ActionType.HELP_REQUESTED, helpType: Lifeline.FIFTY_FIFTY });
    assert.deepEqual(state, { ...before, errorMessage: "" });
  });

  test("opening the chat clears the unread badge; closing keeps messages", () => {
    let state = reduce(midGameState({ chatOpen: false }), { type: ActionType.CHAT_OPENED });
    assert.equal(state.chatOpen, true);
    assert.equal(state.chatUnreadCount, 0);
    state = reduce(state, { type: ActionType.CHAT_CLOSED });
    assert.equal(state.chatOpen, false);
    assert.equal(state.chatMessages.length, 1);
  });

  test("typing and sending a chat message", () => {
    let state = reduce(midGameState(), { type: ActionType.CHAT_INPUT_CHANGED, text: "gg" });
    assert.equal(state.chatInput, "gg");
    state = reduce(state, { type: ActionType.CHAT_MESSAGE_SENT });
    assert.equal(state.chatInput, "");
  });

  test("closing the friend popup", () => {
    const state = reduce(midGameState(), { type: ActionType.FRIEND_POPUP_CLOSED });
    assert.deepEqual(state.friendPopup, CLOSED_POPUP);
  });

  test("play again: back to the welcome screen with an empty race", () => {
    const state = reduce(midGameState({ phase: Phase.FINISHED }), { type: ActionType.PLAY_AGAIN });
    assert.equal(state.phase, Phase.INTRO);
    assert.equal(state.raceStandings, EMPTY_RACE_STANDINGS);
    assert.equal(state.previousRaceStandings, EMPTY_RACE_STANDINGS);
    assert.equal(state.settledRaceStandings, EMPTY_RACE_STANDINGS);
  });
});

describe("derived values and guards", () => {
  test("the race track shows live standings, else the starting grid, else nothing", () => {
    const live = standings(300);
    assert.equal(selectRaceStandings({ raceStandings: live, gameInfo: GAME_INFO }), live);
    assert.equal(
      selectRaceStandings({ raceStandings: EMPTY_RACE_STANDINGS, gameInfo: GAME_INFO }),
      GAME_INFO.raceStandings
    );
    assert.equal(
      selectRaceStandings({ raceStandings: EMPTY_RACE_STANDINGS, gameInfo: null }),
      EMPTY_RACE_STANDINGS
    );
  });

  test("an answer needs an open, unlocked question and an option 50/50 kept", () => {
    const open = midGameState({ lockedAnswer: false, removedOptions: ["A"] });
    assert.equal(canChooseAnswer(open, "B"), true);
    assert.equal(canChooseAnswer(open, "A"), false);
    assert.equal(canChooseAnswer({ ...open, lockedAnswer: true }, "B"), false);
    assert.equal(canChooseAnswer({ ...open, question: null }, "B"), false);
  });

  test("lifelines need an open, unlocked question", () => {
    const open = midGameState({ lockedAnswer: false });
    assert.equal(canUseHelp(open), true);
    assert.equal(canUseHelp({ ...open, lockedAnswer: true }), false);
    assert.equal(canUseHelp({ ...open, question: null }), false);
  });

  test("seconds left round up and never go negative", () => {
    assert.equal(secondsUntil(10_000, 0), 10);
    assert.equal(secondsUntil(10_000, 1), 10);
    assert.equal(secondsUntil(10_000, 9_001), 1);
    assert.equal(secondsUntil(10_000, 10_000), 0);
    assert.equal(secondsUntil(10_000, 12_000), 0);
  });
});

describe("a whole solo game", () => {
  test("walks through every screen in order", () => {
    const phases = [];
    const record = (state) => {
      phases.push(state.phase);
      return state;
    };
    const resultFor = (questionId) => ({
      questionId,
      correctOption: "B",
      correctAnswer: "Mars",
      answers: [{ playerId: SELF_ID, selectedOption: "B", isCorrect: true, pointsEarned: 600 }],
      leaderboard: [],
      raceStandings: standings(600 * questionId),
    });

    let state = initialState;
    for (const action of [
      { type: ActionType.SOCKET_CONNECTED, socketId: SELF_ID },
      server(ServerEvent.CONNECTED, { sid: SELF_ID, matchmakingSeconds: 2, questionSeconds: 3, questionsPerGame: 2 }),
      { type: ActionType.PLAYER_NAME_CHANGED, name: "Dana" },
      { type: ActionType.QUEUE_JOINED, profile: { ride: "motorcycle", paint: "blue" }, socketId: SELF_ID },
      server(ServerEvent.MATCHMAKING_STATUS, { secondsLeft: 2, playerCount: 1, players: ["Dana"], playerProfiles: [] }),
      server(ServerEvent.GAME_STARTED, GAME_INFO),
      server(ServerEvent.RACE_STANDINGS, standings(0)),
      server(ServerEvent.PLAYER_STATE, { helps: { fiftyFifty: true, doubleScore: true, callFriend: true } }),
      server(ServerEvent.QUESTION, { ...QUESTION, id: 1, seconds: 3 }),
      { type: ActionType.ANSWER_CHOSEN, option: "B" },
      server(ServerEvent.SOUND_EFFECT, { name: "submit_answer", url: "/sounds/submit_answer.mp3" }),
      server(ServerEvent.ANSWER_RECEIVED, { questionId: 1, selectedOption: "B" }),
      server(ServerEvent.QUESTION_RESULT, resultFor(1)),
      server(ServerEvent.QUESTION, { ...QUESTION, id: 2, seconds: 3 }),
      server(ServerEvent.QUESTION_RESULT, resultFor(2)),
      server(ServerEvent.GAME_FINISHED, { questionCount: 2, leaderboard: [], raceStandings: standings(1200) }),
      server(ServerEvent.CHAT_HISTORY_CLEARED, {}),
      { type: ActionType.PLAY_AGAIN },
    ]) {
      state = record(reduce(state, action));
    }

    assert.deepEqual(
      phases.filter((phase, index) => phase !== phases[index - 1]),
      [Phase.INTRO, Phase.WAITING, Phase.GAME, Phase.RESULT, Phase.GAME, Phase.RESULT, Phase.FINISHED, Phase.INTRO]
    );
    assert.equal(state.currentPlayerId, SELF_ID);
    assert.equal(state.playerName, "Dana");
  });
});
