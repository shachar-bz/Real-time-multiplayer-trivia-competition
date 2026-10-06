/**
 * Sound catalogue: effect name -> file path on the game server (SERVER_URL).
 * The server names some of these in `sound_effect` events; the client plays
 * the others itself (clicks, countdown, ticking clock, round result).
 */

export const SOUND_EFFECTS = {
  click: "/sounds/click.mp3",
  correct_answer: "/sounds/correct_answer.mp3",
  wrong_answer: "/sounds/wrong_answer.mp3",
  win_game: "/sounds/win_game.mp3",
  submit_answer: "/sounds/submit_answer.mp3",
  click_possible_answer: "/sounds/click_possible_answer.mp3",
  call_friend: "/sounds/call_friend.mp3",
  ticking_clock: "/sounds/ticking_clock.mp3",
  game_countdown: "/sounds/game_countdown.mp3",
  no_answer: "/sounds/no_answer.mp3",
};

/** The sound that tells a player how their round went: no answer, right or wrong. */
export function roundResultSound(questionResult, playerId) {
  const playerAnswer = questionResult.answers.find((answer) => answer.playerId === playerId);

  if (!playerAnswer?.selectedOption) {
    return "no_answer";
  }

  return playerAnswer.isCorrect ? "correct_answer" : "wrong_answer";
}
