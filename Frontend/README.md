# Frontend

The browser client for the trivia race: Next.js 16 (app router), React 19,
plain JavaScript, CSS modules and `socket.io-client`. It talks only to the
game server in `../Backend`.

## Run it

```bash
npm ci
npm run dev          # http://localhost:8081, expects the server on http://localhost:8080
```

To use a server somewhere else, `cp .env.example .env` and set
`NEXT_PUBLIC_SERVER_URL` (it is baked in at build time, so restart or rebuild).

| Script          | What it does                                      |
| --------------- | ------------------------------------------------- |
| `npm run dev`   | Development server on port 8081                   |
| `npm run build` | Production build                                  |
| `npm start`     | Serve the production build on port 8081           |
| `npm test`      | Unit tests for `lib/` with `node:test` (no extra dependencies) |
| `npm run lint`  | ESLint with Next.js' core-web-vitals rules        |

## How it fits together

```
 server ──Socket.IO event──► hooks/useTriviaGame ──dispatch──► lib/gameReducer ──state──► app/page.js
    ▲                          │                                 (pure)                  │
    │                          ├─► hooks/useSoundEffects (sounds)                        ▼
    └────── socket.emit ◄──────┴──────────── actions (join, answer, lifeline, chat) ◄── components/
```

- **`lib/gameReducer.js`** holds every state transition. Each server event is
  dispatched with its wire name as the action type, so the reducer reads like
  the protocol: one case per event. It is pure (time and socket id are passed
  in) and fully unit tested.
- **`hooks/useTriviaGame.js`** owns the socket. It forwards every server event
  to the reducer and performs the side effects that go with it: sounds, the
  question clock, chat scrolling and the messages sent back to the server.
- **`app/page.js`** only picks the screen for the current phase.

## Layout

```
app/                  the route: layout.js, page.js, globals.css
components/           screens by feature, each with its CSS module
  welcome/            WelcomeScreen: name, ride and paint
  matchmaking/        MatchmakingScreen: lobby countdown and starting grid
  game/               GameScreen with QuestionStage, FriendModal, ChatPanel, RaceTrack
  results/            RoundResult (after each question), FinalLeaderboard
hooks/
  useTriviaGame.js    socket + reducer + side effects; returns { state, actions, ... }
  useSoundEffects.js  audio cache, one-shot and looping sounds, autoplay priming
lib/                  framework-free modules, also run by the tests in Node
  protocol.js         client/server event names and lifeline ids (the wire contract)
  gameReducer.js      game state and its transitions
  config.js           server URL and default timings
  sounds.js           sound catalogue and the round-result sound rule
  vehicles.js         ride and paint catalogue with forgiving lookups
  race.js             race progress and score ordering
  classNames.js       cx() for conditional class names
tests/                node:test suites for lib/
```

## Conventions

- `lib/` never imports React or Next.js, and imports inside it use explicit
  `.js` extensions so Node can run it without a bundler. Everything else
  imports through the `@/` alias (`jsconfig.json`).
- Side effects live in hooks, never in the reducer.
- Adding a server event: add it to `lib/protocol.js`, add a reducer case and
  a test, then any sound or scroll it needs in `useTriviaGame`.
