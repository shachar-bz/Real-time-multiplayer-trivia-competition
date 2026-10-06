/**
 * The Socket.IO protocol spoken with the game server.
 *
 * These names are the wire contract and mirror the backend's ClientEvent /
 * ServerEvent constants. Change them only together with the server.
 */

/** Events the browser emits. */
export const ClientEvent = Object.freeze({
  JOIN_QUEUE: "join_queue", // { name, ride, paint }
  LEAVE_QUEUE: "leave_queue", // no payload
  ANSWER: "answer", // { questionId, option }
  USE_HELP: "use_help", // { questionId, helpType: Lifeline }
  CHAT_REQUEST_HISTORY: "chat_request_history", // { game_id }
  CHAT_OPEN: "chat_open", // { game_id }
  CHAT_SEND_MESSAGE: "chat_send_message", // { game_id, content }
});

/** Events the server emits. */
export const ServerEvent = Object.freeze({
  CONNECTED: "connected", // { sid, matchmakingSeconds, questionSeconds, questionsPerGame, profileChoices }
  ERROR_MESSAGE: "error_message", // { message }
  MATCHMAKING_STATUS: "matchmaking_status", // { secondsLeft, playerCount, players, playerProfiles }
  GAME_STARTED: "game_started", // { gameId, players, playerProfiles, questionCount, questionSeconds, raceStandings }
  PLAYER_STATE: "player_state", // { helps, profile }
  QUESTION: "question", // { id, index, total, text, topic, difficulty, seconds, options: [{ key, text }] }
  ANSWER_RECEIVED: "answer_received", // { questionId, selectedOption }
  RACE_STANDINGS: "race_standings", // { finishScore, players }
  HELP_USED: "help_used", // { questionId, helpType, helps, removedOptions | doubleScoreActive | message+confidence+friendAnswered }
  QUESTION_TIMER_PAUSED: "question_timer_paused", // { questionId, secondsLeft, callerId, callerName, message }
  QUESTION_TIMER_RESUMED: "question_timer_resumed", // { questionId, secondsLeft }
  QUESTION_RESULT: "question_result", // { questionId, correctOption, correctAnswer, answers, leaderboard, raceStandings }
  GAME_FINISHED: "game_finished", // { questionCount, leaderboard, raceStandings }
  SOUND_EFFECT: "sound_effect", // { name, url }
  CHAT_NEW_MESSAGE: "chat_new_message", // { id, game_id, user_id, username, content, timestamp }
  CHAT_HISTORY: "chat_history", // [{ id, username, content, timestamp, is_own }]
  CHAT_UNREAD_UPDATE: "chat_unread_update", // { unread_count }
  CHAT_HISTORY_CLEARED: "chat_history_cleared", // {}
});

/** Lifeline ids, sent as `helpType` in `use_help` and echoed back in `help_used`. */
export const Lifeline = Object.freeze({
  FIFTY_FIFTY: "fifty_fifty",
  DOUBLE_SCORE: "double_score",
  CALL_A_FRIEND: "call_a_friend",
});
