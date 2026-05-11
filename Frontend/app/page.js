"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { io } from "socket.io-client";


const SERVER_URL = "http://localhost:8080";
const DEFAULT_MATCHMAKING_SECONDS = 30;
const DEFAULT_QUESTION_SECONDS = 12;
const DEFAULT_QUESTIONS_PER_GAME = 10;
const OPTION_LABELS = ["A", "B", "C", "D"];


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
    });
    socket.on("question", (nextQuestion) => {
      setPhase("game");
      setQuestion(nextQuestion);
      setSelectedOption(null);
      setLockedAnswer(false);
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
    socket.on("game_finished", (summary) => {
      setPhase("finished");
      setLeaderboard(summary.leaderboard);
      setQuestion(null);
      setResult(null);
      setGameInfo(null);
      setQuestionEndsAt(null);
    });
    socket.on("error_message", (error) => setErrorMessage(error.message));

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
    if (!question || lockedAnswer) {
      return;
    }

    setSelectedOption(option);
    setLockedAnswer(true);
    socketRef.current?.emit("answer", {
      questionId: question.id,
      option,
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
          <div className="options">
            {question.options.map((option) => (
              <button
                className={selectedOption === option.key ? "option selected" : "option"}
                disabled={lockedAnswer}
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
              {myResult.isCorrect ? "You got 1 point." : "No point this round."}
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
