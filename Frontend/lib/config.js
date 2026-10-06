/**
 * Client configuration.
 *
 * SERVER_URL is the Python game server: it hosts the Socket.IO endpoint and
 * serves the sound files. Set NEXT_PUBLIC_SERVER_URL (see .env.example) to
 * point elsewhere; Next.js copies it into the browser bundle at build time.
 *
 * The DEFAULT_* timings are placeholders shown until the server sends its
 * real settings in the `connected` event.
 */

export const SERVER_URL = process.env.NEXT_PUBLIC_SERVER_URL || "http://localhost:8080";

export const DEFAULT_MATCHMAKING_SECONDS = 30;
export const DEFAULT_QUESTION_SECONDS = 20;
export const DEFAULT_QUESTIONS_PER_GAME = 10;

/** The lobby plays the "game_countdown" sound when this many seconds are left. */
export const GAME_COUNTDOWN_SECONDS = 4;
