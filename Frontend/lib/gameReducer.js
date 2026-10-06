/**
 * The trivia client's game state, as one pure reducer.
 *
 *   server event or player action  ->  gameReducer(state, action)  ->  next state
 *
 * Every Socket.IO event from the server is dispatched with the event name as
 * its `type` (see ServerEvent in ./protocol.js) and the event data as
 * `payload`. Things the player does, the socket's own lifecycle and the
 * question clock use the ActionType values below.
 *
 * The reducer never touches the socket, the clock or the speakers. The caller
 * (hooks/useTriviaGame.js) does that and passes in the two facts the reducer
 * needs: `now` (Date.now() when the event arrived) and `selfId` (this
 * browser's socket id).
 */

import {
  DEFAULT_MATCHMAKING_SECONDS,
  DEFAULT_QUESTIONS_PER_GAME,
  DEFAULT_QUESTION_SECONDS,
} from "./config.js";
import { Lifeline, ServerEvent } from "./protocol.js";

/** Which screen is showing. */
export const Phase = Object.freeze({
  INTRO: "intro", // welcome screen: racer name and ride
  WAITING: "waiting", // matchmaking lobby
  GAME: "game", // a question is on screen
  RESULT: "result", // the round's correct answer and race progress
  FINISHED: "finished", // final leaderboard
});

/** What the call-a-friend popup is showing. */
export const FriendPopupKind = Object.freeze({
  NONE: "",
  CALLER_LOADING: "caller_loading", // we called a friend and wait for the answer
  OBSERVER_WAITING: "observer_waiting", // another racer is calling; the timer is paused
  RESULT: "result", // the friend's answer
});

/** Actions that are not server events. */
export const ActionType = Object.freeze({
  SOCKET_CONNECTED: "socket/connected", // { socketId }
  SOCKET_DISCONNECTED: "socket/disconnected",
  CLOCK_TICKED: "clock/ticked", // { secondsLeft }
  PLAYER_NAME_CHANGED: "player/nameChanged", // { name }
  QUEUE_JOINED: "player/queueJoined", // { profile: { ride, paint }, socketId }
  LOBBY_LEFT: "player/lobbyLeft",
  ANSWER_CHOSEN: "player/answerChosen", // { option }
  HELP_REQUESTED: "player/helpRequested", // { helpType }
  CHAT_OPENED: "player/chatOpened",
  CHAT_CLOSED: "player/chatClosed",
  CHAT_INPUT_CHANGED: "player/chatInputChanged", // { text }
  CHAT_MESSAGE_SENT: "player/chatMessageSent",
  FRIEND_POPUP_CLOSED: "player/friendPopupClosed",
  PLAY_AGAIN: "player/playAgain",
});

export const EMPTY_RACE_STANDINGS = {
  finishScore: 0,
  players: [],
};

const ALL_HELPS_AVAILABLE = {
  fiftyFifty: true,
  doubleScore: true,
  callFriend: true,
};

const CLOSED_FRIEND_POPUP = {
  open: false,
  loading: false,
  message: "",
  confidence: null,
  friendAnswered: null,
  kind: FriendPopupKind.NONE,
};

const CALLER_LOADING_POPUP = {
  open: true,
  loading: true,
  message: "Calling your funniest friend...",
  confidence: null,
  friendAnswered: null,
  kind: FriendPopupKind.CALLER_LOADING,
};

const OBSERVER_WAITING_POPUP = {
  open: true,
  loading: true,
  message: "Someone is calling his friend.",
  confidence: null,
  friendAnswered: null,
  kind: FriendPopupKind.OBSERVER_WAITING,
};

/** Chat starts closed and empty in every game. */
const RESET_CHAT = {
  chatOpen: false,
  chatMessages: [],
  chatInput: "",
  chatUnreadCount: 0,
};

export const initialState = {
  phase: Phase.INTRO,
  connectionStatus: "Disconnected",
  currentPlayerId: null,
  playerName: "",
  config: {
    matchmakingSeconds: DEFAULT_MATCHMAKING_SECONDS,
    questionSeconds: DEFAULT_QUESTION_SECONDS,
    questionsPerGame: DEFAULT_QUESTIONS_PER_GAME,
  },
  waiting: {
    secondsLeft: DEFAULT_MATCHMAKING_SECONDS,
    playerCount: 0,
    players: [],
    playerProfiles: [],
  },
  gameInfo: null,

  // The current question and this player's choices for it.
  question: null,
  selectedOption: null,
  lockedAnswer: false,
  removedOptions: [],
  doubleScoreActive: false,
  helps: ALL_HELPS_AVAILABLE,
  friendPopup: CLOSED_FRIEND_POPUP,
  timeLeft: DEFAULT_QUESTION_SECONDS,
  questionEndsAt: null, // epoch ms while the clock runs; null when stopped or paused

  result: null,
  leaderboard: [],

  // raceStandings is live: race_standings events move it during a question.
  // settledRaceStandings is the standings at the end of the last round, and
  // previousRaceStandings is what the result screen animates *from*, so each
  // round's animation covers the whole round, not the last live update.
  raceStandings: EMPTY_RACE_STANDINGS,
  previousRaceStandings: EMPTY_RACE_STANDINGS,
  settledRaceStandings: EMPTY_RACE_STANDINGS,

  errorMessage: "",
  ...RESET_CHAT,
};

export function gameReducer(state, action) {
  switch (action.type) {
    // ---- socket lifecycle and clock --------------------------------------

    case ActionType.SOCKET_CONNECTED:
      return { ...state, connectionStatus: "Connected", currentPlayerId: action.socketId };

    case ActionType.SOCKET_DISCONNECTED:
      return { ...state, connectionStatus: "Disconnected" };

    // The clock ticks four times a second but the display counts whole seconds,
    // so keep the same state object when the second has not changed and let
    // React skip the render.
    case ActionType.CLOCK_TICKED:
      return action.secondsLeft === state.timeLeft
        ? state
        : { ...state, timeLeft: action.secondsLeft };

    // ---- server events ---------------------------------------------------

    case ServerEvent.CONNECTED: {
      const serverConfig = action.payload;
      return {
        ...state,
        currentPlayerId: serverConfig.sid,
        config: {
          matchmakingSeconds: serverConfig.matchmakingSeconds,
          questionSeconds: serverConfig.questionSeconds,
          questionsPerGame: serverConfig.questionsPerGame,
        },
      };
    }

    case ServerEvent.MATCHMAKING_STATUS:
      return { ...state, phase: Phase.WAITING, waiting: action.payload };

    case ServerEvent.GAME_STARTED: {
      const gameInfo = action.payload;
      const startingStandings = gameInfo.raceStandings || EMPTY_RACE_STANDINGS;
      return {
        ...state,
        phase: Phase.GAME,
        gameInfo,
        leaderboard: [],
        raceStandings: startingStandings,
        previousRaceStandings: startingStandings,
        settledRaceStandings: startingStandings,
        result: null,
        errorMessage: "",
        ...RESET_CHAT,
        helps: ALL_HELPS_AVAILABLE,
        friendPopup: CLOSED_FRIEND_POPUP,
      };
    }

    case ServerEvent.PLAYER_STATE:
      return { ...state, helps: action.payload.helps };

    case ServerEvent.QUESTION: {
      const question = action.payload;
      return {
        ...state,
        phase: Phase.GAME,
        question,
        selectedOption: null,
        lockedAnswer: false,
        removedOptions: [],
        doubleScoreActive: false,
        friendPopup: CLOSED_FRIEND_POPUP,
        result: null,
        timeLeft: question.seconds,
        questionEndsAt: action.now + question.seconds * 1000,
      };
    }

    case ServerEvent.ANSWER_RECEIVED:
      return { ...state, selectedOption: action.payload.selectedOption, lockedAnswer: true };

    case ServerEvent.SOUND_EFFECT:
      return state; // audio only

    case ServerEvent.CHAT_NEW_MESSAGE: {
      const message = action.payload;
      const normalizedMessage = {
        ...message,
        is_own: message.is_own ?? message.user_id === action.selfId,
      };
      return { ...state, chatMessages: [...state.chatMessages, normalizedMessage] };
    }

    case ServerEvent.CHAT_HISTORY:
      return { ...state, chatMessages: action.payload };

    case ServerEvent.CHAT_UNREAD_UPDATE:
      return { ...state, chatUnreadCount: action.payload.unread_count || 0 };

    case ServerEvent.CHAT_HISTORY_CLEARED:
      return { ...state, chatMessages: [], chatUnreadCount: 0 };

    case ServerEvent.RACE_STANDINGS:
      return { ...state, raceStandings: action.payload || EMPTY_RACE_STANDINGS };

    case ServerEvent.QUESTION_RESULT: {
      const questionResult = action.payload;
      const roundStandings = questionResult.raceStandings || EMPTY_RACE_STANDINGS;
      return {
        ...state,
        phase: Phase.RESULT,
        result: questionResult,
        leaderboard: questionResult.leaderboard,
        previousRaceStandings: state.settledRaceStandings,
        raceStandings: roundStandings,
        settledRaceStandings: roundStandings,
        questionEndsAt: null,
        timeLeft: 0,
      };
    }

    case ServerEvent.HELP_USED:
      return applyHelpUsed({ ...state, helps: action.payload.helps }, action.payload);

    case ServerEvent.QUESTION_TIMER_PAUSED: {
      const pause = action.payload;
      const weAreCalling = pause.callerId === action.selfId;
      return {
        ...state,
        timeLeft: pause.secondsLeft,
        questionEndsAt: null,
        friendPopup: weAreCalling ? CALLER_LOADING_POPUP : OBSERVER_WAITING_POPUP,
      };
    }

    case ServerEvent.QUESTION_TIMER_RESUMED: {
      const resume = action.payload;
      const { kind } = state.friendPopup;
      const waitingForFriend =
        kind === FriendPopupKind.OBSERVER_WAITING || kind === FriendPopupKind.CALLER_LOADING;
      return {
        ...state,
        timeLeft: resume.secondsLeft,
        questionEndsAt: action.now + resume.secondsLeft * 1000,
        friendPopup: waitingForFriend ? CLOSED_FRIEND_POPUP : state.friendPopup,
      };
    }

    case ServerEvent.GAME_FINISHED: {
      const summary = action.payload;
      const finalStandings = summary.raceStandings || EMPTY_RACE_STANDINGS;
      return {
        ...state,
        phase: Phase.FINISHED,
        leaderboard: summary.leaderboard,
        previousRaceStandings: state.settledRaceStandings,
        raceStandings: finalStandings,
        settledRaceStandings: finalStandings,
        question: null,
        result: null,
        gameInfo: null,
        questionEndsAt: null,
        ...RESET_CHAT,
        friendPopup: CLOSED_FRIEND_POPUP,
      };
    }

    case ServerEvent.ERROR_MESSAGE:
      return {
        ...state,
        errorMessage: action.payload.message,
        friendPopup: state.friendPopup.loading ? CLOSED_FRIEND_POPUP : state.friendPopup,
      };

    // ---- player actions --------------------------------------------------

    case ActionType.PLAYER_NAME_CHANGED:
      return { ...state, playerName: action.name };

    case ActionType.QUEUE_JOINED: {
      // Show the lobby with ourselves in it right away, before the server answers.
      const name = state.playerName.trim();
      const { ride, paint } = action.profile || {};
      return {
        ...state,
        errorMessage: "",
        phase: Phase.WAITING,
        waiting: {
          secondsLeft: state.config.matchmakingSeconds,
          playerCount: 1,
          players: [name],
          playerProfiles: [
            {
              id: action.socketId || state.currentPlayerId || "current-player",
              name,
              ride,
              paint,
            },
          ],
        },
      };
    }

    case ActionType.LOBBY_LEFT:
      return {
        ...state,
        errorMessage: "",
        waiting: {
          secondsLeft: state.config.matchmakingSeconds,
          playerCount: 0,
          players: [],
          playerProfiles: [],
        },
        phase: Phase.INTRO,
      };

    case ActionType.ANSWER_CHOSEN:
      return { ...state, selectedOption: action.option, lockedAnswer: true };

    case ActionType.HELP_REQUESTED:
      return {
        ...state,
        errorMessage: "",
        friendPopup:
          action.helpType === Lifeline.CALL_A_FRIEND ? CALLER_LOADING_POPUP : state.friendPopup,
      };

    case ActionType.CHAT_OPENED:
      return { ...state, chatOpen: true, chatUnreadCount: 0 };

    case ActionType.CHAT_CLOSED:
      return { ...state, chatOpen: false };

    case ActionType.CHAT_INPUT_CHANGED:
      return { ...state, chatInput: action.text };

    case ActionType.CHAT_MESSAGE_SENT:
      return { ...state, chatInput: "" };

    case ActionType.FRIEND_POPUP_CLOSED:
      return { ...state, friendPopup: CLOSED_FRIEND_POPUP };

    case ActionType.PLAY_AGAIN:
      return {
        ...state,
        raceStandings: EMPTY_RACE_STANDINGS,
        previousRaceStandings: EMPTY_RACE_STANDINGS,
        settledRaceStandings: EMPTY_RACE_STANDINGS,
        phase: Phase.INTRO,
      };

    default:
      return state;
  }
}

function applyHelpUsed(state, help) {
  switch (help.helpType) {
    case Lifeline.FIFTY_FIFTY:
      return { ...state, removedOptions: help.removedOptions };
    case Lifeline.DOUBLE_SCORE:
      return { ...state, doubleScoreActive: Boolean(help.doubleScoreActive) };
    case Lifeline.CALL_A_FRIEND:
      return {
        ...state,
        friendPopup: {
          open: true,
          loading: false,
          message: help.message,
          confidence: help.confidence,
          friendAnswered: help.friendAnswered,
          kind: FriendPopupKind.RESULT,
        },
      };
    default:
      return state;
  }
}

// ---- derived values and guards (pure, used by the hook and the screens) ----

/** The standings the race track shows: live ones, or the starting grid until the first update. */
export function selectRaceStandings(state) {
  return state.raceStandings?.players?.length > 0
    ? state.raceStandings
    : state.gameInfo?.raceStandings || EMPTY_RACE_STANDINGS;
}

/** A player may answer once per question, and not with an option that 50/50 removed. */
export function canChooseAnswer(state, option) {
  return Boolean(state.question) && !state.lockedAnswer && !state.removedOptions.includes(option);
}

/** Lifelines can only be used on an open question that is not answered yet. */
export function canUseHelp(state) {
  return Boolean(state.question) && !state.lockedAnswer;
}

/** Whole seconds left until `endsAt` (rounded up, never negative). */
export function secondsUntil(endsAt, now) {
  return Math.max(0, Math.ceil((endsAt - now) / 1000));
}
