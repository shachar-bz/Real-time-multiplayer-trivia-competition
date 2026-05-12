"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";


const SERVER_URL = "http://localhost:8080";
const DEFAULT_MATCHMAKING_SECONDS = 30;
const DEFAULT_QUESTION_SECONDS = 20;
const DEFAULT_QUESTIONS_PER_GAME = 10;
const HELP_FIFTY_FIFTY = "fifty_fifty";
const HELP_DOUBLE_SCORE = "double_score";
const HELP_CALL_A_FRIEND = "call_a_friend";


export default function Home() {
  const socketRef = useRef(null);
  const [phase, setPhase] = useState("intro");
  const [connectionStatus, setConnectionStatus] = useState("Disconnected");
  const [playerName, setPlayerName] = useState("");
  const [config, setConfig] = useState({
    matchmakingSeconds: DEFAULT_MATCHMAKING_SECONDS,
    questionSeconds: DEFAULT_QUESTION_SECONDS,
    questionsPerGame: DEFAULT_QUESTIONS_PER_GAME,
  });
  const [waiting, setWaiting] = useState({
    secondsLeft: DEFAULT_MATCHMAKING_SECONDS,
    playerCount: 0,
    players: [],
  });
  const [gameInfo, setGameInfo] = useState(null);
  const [question, setQuestion] = useState(null);
  const [selectedOption, setSelectedOption] = useState(null);
  const [lockedAnswer, setLockedAnswer] = useState(false);
  const [removedOptions, setRemovedOptions] = useState([]);
  const [doubleScoreActive, setDoubleScoreActive] = useState(false);
  const [helps, setHelps] = useState({
    fiftyFifty: true,
    doubleScore: true,
    callFriend: true,
  });
  const [friendPopup, setFriendPopup] = useState({
    open: false,
    loading: false,
    message: "",
    confidence: null,
    friendAnswered: null,
    kind: "",
  });
  const [timeLeft, setTimeLeft] = useState(DEFAULT_QUESTION_SECONDS);
  const [questionEndsAt, setQuestionEndsAt] = useState(null);
  const [result, setResult] = useState(null);
  const [leaderboard, setLeaderboard] = useState([]);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    const socket = io(SERVER_URL, {
      autoConnect: true,
      transports: ["websocket", "polling"],
    });
    socketRef.current = socket;

    socket.on("connect", () => setConnectionStatus("Connected"));
    socket.on("disconnect", () => setConnectionStatus("Disconnected"));
    socket.on("connected", (serverConfig) => {
      setConfig({
        matchmakingSeconds: serverConfig.matchmakingSeconds,
        questionSeconds: serverConfig.questionSeconds,
        questionsPerGame: serverConfig.questionsPerGame,
      });
    });
    socket.on("matchmaking_status", (status) => {
      setPhase("waiting");
      setWaiting(status);
    });
    socket.on("game_started", (info) => {
      setPhase("game");
      setGameInfo(info);
      setLeaderboard([]);
      setResult(null);
      setErrorMessage("");
      setHelps({
        fiftyFifty: true,
        doubleScore: true,
        callFriend: true,
      });
      setFriendPopup({
        open: false,
        loading: false,
        message: "",
        confidence: null,
        friendAnswered: null,
        kind: "",
      });
    });
    socket.on("player_state", (state) => {
      setHelps(state.helps);
    });
    socket.on("question", (nextQuestion) => {
      setPhase("game");
      setQuestion(nextQuestion);
      setSelectedOption(null);
      setLockedAnswer(false);
      setRemovedOptions([]);
      setDoubleScoreActive(false);
      setFriendPopup({
        open: false,
        loading: false,
        message: "",
        confidence: null,
        friendAnswered: null,
        kind: "",
      });
      setResult(null);
      setTimeLeft(nextQuestion.seconds);
      setQuestionEndsAt(Date.now() + nextQuestion.seconds * 1000);
    });
    socket.on("answer_received", (answer) => {
      setSelectedOption(answer.selectedOption);
      setLockedAnswer(true);
    });
    socket.on("question_result", (questionResult) => {
      setPhase("result");
      setResult(questionResult);
      setLeaderboard(questionResult.leaderboard);
      setQuestionEndsAt(null);
      setTimeLeft(0);
    });
    socket.on("help_used", (helpResult) => {
      setHelps(helpResult.helps);
      if (helpResult.helpType === HELP_FIFTY_FIFTY) {
        setRemovedOptions(helpResult.removedOptions);
      }
      if (helpResult.helpType === HELP_DOUBLE_SCORE) {
        setDoubleScoreActive(Boolean(helpResult.doubleScoreActive));
      }
      if (helpResult.helpType === HELP_CALL_A_FRIEND) {
        setFriendPopup({
          open: true,
          loading: false,
          message: helpResult.message,
          confidence: helpResult.confidence,
          friendAnswered: helpResult.friendAnswered,
          kind: "result",
        });
      }
    });
    socket.on("question_timer_paused", (pauseInfo) => {
      setTimeLeft(pauseInfo.secondsLeft);
      setQuestionEndsAt(null);
      if (pauseInfo.callerId === socket.id) {
        setFriendPopup({
          open: true,
          loading: true,
          message: "Calling your funniest friend...",
          confidence: null,
          friendAnswered: null,
          kind: "caller_loading",
        });
        return;
      }

      setFriendPopup({
        open: true,
        loading: true,
        message: "Someone is calling his friend.",
        confidence: null,
        friendAnswered: null,
        kind: "observer_waiting",
      });
    });
    socket.on("question_timer_resumed", (resumeInfo) => {
      setTimeLeft(resumeInfo.secondsLeft);
      setQuestionEndsAt(Date.now() + resumeInfo.secondsLeft * 1000);
      setFriendPopup((currentPopup) => {
        if (currentPopup.kind === "observer_waiting" || currentPopup.kind === "caller_loading") {
          return {
            open: false,
            loading: false,
            message: "",
            confidence: null,
            friendAnswered: null,
            kind: "",
          };
        }

        return currentPopup;
      });
    });
    socket.on("game_finished", (summary) => {
      setPhase("finished");
      setLeaderboard(summary.leaderboard);
      setQuestion(null);
      setResult(null);
      setGameInfo(null);
      setQuestionEndsAt(null);
      setFriendPopup({
        open: false,
        loading: false,
        message: "",
        confidence: null,
        friendAnswered: null,
        kind: "",
      });
    });
    socket.on("error_message", (error) => {
      setErrorMessage(error.message);
      setFriendPopup((currentPopup) =>
        currentPopup.loading
          ? {
              open: false,
              loading: false,
              message: "",
              confidence: null,
              friendAnswered: null,
              kind: "",
            }
          : currentPopup
      );
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  useEffect(() => {
    if (!questionEndsAt) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setTimeLeft(Math.max(0, Math.ceil((questionEndsAt - Date.now()) / 1000)));
    }, 250);

    return () => window.clearInterval(timer);
  }, [questionEndsAt]);

  const myResult = useMemo(() => {
    if (!result || !socketRef.current) {
      return null;
    }

    return result.answers.find((answer) => answer.playerId === socketRef.current.id);
  }, [result]);

  function joinQueue(event) {
    event.preventDefault();
    setErrorMessage("");
    setPhase("waiting");
    setWaiting({
      secondsLeft: config.matchmakingSeconds,
      playerCount: 1,
      players: [playerName.trim() || "Player"],
    });
    socketRef.current?.emit("join_queue", { name: playerName });
  }

  function chooseAnswer(option) {
    if (!question || lockedAnswer || removedOptions.includes(option)) {
      return;
    }

    setSelectedOption(option);
    setLockedAnswer(true);
    socketRef.current?.emit("answer", {
      questionId: question.id,
      option,
    });
  }

  function useHelp(helpType) {
    if (!question || lockedAnswer) {
      return;
    }

    setErrorMessage("");
    if (helpType === HELP_CALL_A_FRIEND) {
      setFriendPopup({
        open: true,
        loading: true,
        message: "Calling your funniest friend...",
        confidence: null,
        friendAnswered: null,
        kind: "caller_loading",
      });
    }
    socketRef.current?.emit("use_help", {
      questionId: question.id,
      helpType,
    });
  }

  return (
    <main className="shell">
      <section className="topbar" aria-label="Game status">
        <div>
          <p className="eyebrow">Multiplayer Trivia</p>
          <h1>Socket.IO Competition</h1>
        </div>
        <span className={connectionStatus === "Connected" ? "status online" : "status"}>
          {connectionStatus}
        </span>
      </section>

      {phase === "intro" && (
        <section className="panel">
          <h2>Join the next game</h2>
          <p className="muted">
            The server opens matchmaking for {config.matchmakingSeconds} seconds, then starts a{" "}
            {config.questionsPerGame}-question trivia round with everyone who joined.
          </p>
          <form className="joinForm" onSubmit={joinQueue}>
            <label htmlFor="playerName">Player name</label>
            <div className="inputRow">
              <input
                id="playerName"
                maxLength={24}
                onChange={(event) => setPlayerName(event.target.value)}
                placeholder="Enter your name"
                value={playerName}
              />
              <button type="submit">Start</button>
            </div>
          </form>
        </section>
      )}

      {phase === "waiting" && (
        <section className="panel center">
          <p className="eyebrow">Matchmaking</p>
          <div className="countdown">{waiting.secondsLeft}</div>
          <h2>Waiting for players</h2>
          <p className="muted">
            {waiting.playerCount} player{waiting.playerCount === 1 ? "" : "s"} ready. The game
            will start even if you are playing solo.
          </p>
          <div className="playerList">
            {waiting.players.map((name) => (
              <span key={name}>{name}</span>
            ))}
          </div>
        </section>
      )}

      {phase === "game" && question && (
        <section className="panel questionPanel">
          <div className="questionMeta">
            <span>
              Question {question.index}/{question.total}
            </span>
            <span>{timeLeft}s</span>
          </div>
          <p className="topic">
            {question.topic} · Difficulty {question.difficulty}
          </p>
          <h2>{question.text}</h2>
          <div className="helps" aria-label="Question helps">
            <button
              className="helpButton"
              disabled={!helps.fiftyFifty || lockedAnswer || removedOptions.length > 0}
              onClick={() => useHelp(HELP_FIFTY_FIFTY)}
              type="button"
            >
              50/50
            </button>
            <button
              className={doubleScoreActive ? "helpButton active" : "helpButton"}
              disabled={!helps.doubleScore || lockedAnswer || doubleScoreActive}
              onClick={() => useHelp(HELP_DOUBLE_SCORE)}
              type="button"
            >
              Double score
            </button>
            <button
              className="helpButton"
              disabled={!helps.callFriend || lockedAnswer || friendPopup.loading}
              onClick={() => useHelp(HELP_CALL_A_FRIEND)}
              type="button"
            >
              Call a friend
            </button>
          </div>
          {doubleScoreActive && (
            <p className="muted">Double score is active for this question.</p>
          )}
          <div className="options">
            {question.options.map((option) => (
              <button
                className={[
                  "option",
                  selectedOption === option.key ? "selected" : "",
                  removedOptions.includes(option.key) ? "removed" : "",
                ].join(" ")}
                disabled={lockedAnswer || removedOptions.includes(option.key)}
                key={option.key}
                onClick={() => chooseAnswer(option.key)}
                type="button"
              >
                <strong>{option.key}</strong>
                <span>{option.text}</span>
              </button>
            ))}
          </div>
          {lockedAnswer && <p className="muted">Answer locked. Waiting for the timer.</p>}
        </section>
      )}

      {phase === "result" && result && (
        <section className="panel">
          <p className="eyebrow">Answer</p>
          <h2>
            Correct answer: {result.correctOption}. {result.correctAnswer}
          </h2>
          {myResult && (
            <p className={myResult.isCorrect ? "feedback good" : "feedback bad"}>
              {myResult.isCorrect
                ? `You got ${myResult.pointsEarned} point${myResult.pointsEarned === 1 ? "" : "s"}.`
                : "No point this round."}
            </p>
          )}
          <Leaderboard leaderboard={leaderboard} />
        </section>
      )}

      {phase === "finished" && (
        <section className="panel">
          <p className="eyebrow">Final leaderboard</p>
          <h2>Game complete</h2>
          <Leaderboard leaderboard={leaderboard} />
          <button className="secondary" onClick={() => setPhase("intro")} type="button">
            Play again
          </button>
        </section>
      )}

      {errorMessage && <p className="error">{errorMessage}</p>}

      {friendPopup.open && (
        <div className="modalBackdrop" role="presentation">
          <section className="modal" aria-label="Call a friend message">
            <p className="eyebrow">Call a friend</p>
            {friendPopup.loading ? (
              <p className="muted">{friendPopup.message}</p>
            ) : (
              <>
                <p className="friendMessage">{friendPopup.message}</p>
              </>
            )}
            <button
              className="secondary"
              disabled={friendPopup.loading}
              onClick={() =>
                setFriendPopup({
                  open: false,
                  loading: false,
                  message: "",
                  confidence: null,
                  friendAnswered: null,
                  kind: "",
                })
              }
              type="button"
            >
              Close
            </button>
          </section>
        </div>
      )}

      {gameInfo && phase !== "finished" && (
        <aside className="gameInfo">
          Players: {gameInfo.players.join(", ")}
        </aside>
      )}
    </main>
  );
}


function Leaderboard({ leaderboard }) {
  return (
    <ol className="leaderboard">
      {leaderboard.map((player, index) => (
        <li key={player.id}>
          <span>
            {index + 1}. {player.name}
            {!player.connected && <em> disconnected</em>}
          </span>
          <strong>{player.score}</strong>
        </li>
      ))}
    </ol>
  );
}
