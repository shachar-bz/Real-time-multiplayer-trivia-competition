"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { io } from "socket.io-client";
import GamePage from "./game_page";
import MatchmakingPage from "./matchmaking_page";
import WelcomePage from "./welcome_page";
import {
  DEFAULT_MATCHMAKING_SECONDS,
  DEFAULT_QUESTIONS_PER_GAME,
  DEFAULT_QUESTION_SECONDS,
  GAME_COUNTDOWN_SECONDS,
  SERVER_URL,
} from "@/lib/config";
import { ClientEvent, Lifeline, ServerEvent } from "@/lib/protocol";


const SOUND_EFFECTS = {
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
const EMPTY_RACE_STANDINGS = {
  finishScore: 0,
  players: [],
};


export default function Home() {
  const socketRef = useRef(null);
  const soundRefs = useRef({});
  const activeSoundRefs = useRef({});
  const gameCountdownPlayedRef = useRef(false);
  const settledRaceStandingsRef = useRef(EMPTY_RACE_STANDINGS);
  const chatListRef = useRef(null);
  const chatOpenRef = useRef(false);
  const [phase, setPhase] = useState("intro");
  const [connectionStatus, setConnectionStatus] = useState("Disconnected");
  const [currentPlayerId, setCurrentPlayerId] = useState(null);
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
    playerProfiles: [],
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
  const [raceStandings, setRaceStandings] = useState(EMPTY_RACE_STANDINGS);
  const [previousRaceStandings, setPreviousRaceStandings] = useState(EMPTY_RACE_STANDINGS);
  const [errorMessage, setErrorMessage] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState("");
  const [chatUnreadCount, setChatUnreadCount] = useState(0);

  const scrollChatToBottom = useCallback(() => {
    window.requestAnimationFrame(() => {
      if (chatListRef.current) {
        chatListRef.current.scrollTop = chatListRef.current.scrollHeight;
      }
    });
  }, []);

  useEffect(() => {
    chatOpenRef.current = chatOpen;
  }, [chatOpen]);

  const ensureSoundAudio = useCallback((name, soundUrl = SOUND_EFFECTS[name]) => {
    if (!soundUrl) {
      return null;
    }

    const absoluteUrl = new URL(soundUrl, SERVER_URL).toString();
    let audio = soundRefs.current[name];
    if (!audio || audio.src !== absoluteUrl) {
      audio = new Audio(absoluteUrl);
      audio.preload = "auto";
      soundRefs.current[name] = audio;
    }

    return audio;
  }, []);

  const playSoundEffect = useCallback(
    (sound) => {
      const name = sound?.name;
      if (!name) {
        return;
      }

      const audio = ensureSoundAudio(name, sound.url || SOUND_EFFECTS[name]);
      if (!audio) {
        return;
      }

      const playback = audio.cloneNode();
      playback.currentTime = 0;
      playback.play().catch(() => {});
    },
    [ensureSoundAudio]
  );

  const playManagedSound = useCallback(
    (name, options = {}) => {
      const audio = ensureSoundAudio(name);
      if (!audio) {
        return;
      }

      audio.pause();
      audio.currentTime = 0;
      audio.loop = Boolean(options.loop);
      activeSoundRefs.current[name] = audio;
      audio.play().catch(() => {});
    },
    [ensureSoundAudio]
  );

  const stopManagedSound = useCallback((name) => {
    const audio = activeSoundRefs.current[name];
    if (!audio) {
      return;
    }

    audio.pause();
    audio.currentTime = 0;
    audio.loop = false;
    delete activeSoundRefs.current[name];
  }, []);

  const primeSoundEffects = useCallback(() => {
    Object.keys(SOUND_EFFECTS).forEach((name) => {
      const audio = ensureSoundAudio(name);
      if (!audio) {
        return;
      }

      audio.muted = true;
      const resetAudio = () => {
        audio.pause();
        audio.currentTime = 0;
        audio.muted = false;
      };
      const playPromise = audio.play();
      if (playPromise) {
        playPromise.then(resetAudio).catch(() => {
          audio.muted = false;
        });
      } else {
        resetAudio();
      }
    });
  }, [ensureSoundAudio]);

  useEffect(() => {
    Object.keys(SOUND_EFFECTS).forEach((name) => {
      ensureSoundAudio(name);
    });

    const socket = io(SERVER_URL, {
      autoConnect: true,
      transports: ["websocket", "polling"],
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      setConnectionStatus("Connected");
      setCurrentPlayerId(socket.id);
    });
    socket.on("disconnect", () => setConnectionStatus("Disconnected"));
    socket.on(ServerEvent.CONNECTED, (serverConfig) => {
      setCurrentPlayerId(serverConfig.sid);
      setConfig({
        matchmakingSeconds: serverConfig.matchmakingSeconds,
        questionSeconds: serverConfig.questionSeconds,
        questionsPerGame: serverConfig.questionsPerGame,
      });
    });
    socket.on(ServerEvent.MATCHMAKING_STATUS, (status) => {
      setPhase("waiting");
      setWaiting(status);
      if (status.secondsLeft > GAME_COUNTDOWN_SECONDS) {
        gameCountdownPlayedRef.current = false;
      }
      if (
        status.secondsLeft === GAME_COUNTDOWN_SECONDS &&
        !gameCountdownPlayedRef.current
      ) {
        gameCountdownPlayedRef.current = true;
        playSoundEffect({ name: "game_countdown" });
      }
    });
    socket.on(ServerEvent.GAME_STARTED, (info) => {
      const startingRaceStandings = info.raceStandings || EMPTY_RACE_STANDINGS;

      stopManagedSound("call_friend");
      stopManagedSound("ticking_clock");
      setPhase("game");
      setGameInfo(info);
      setLeaderboard([]);
      setRaceStandings(startingRaceStandings);
      setPreviousRaceStandings(startingRaceStandings);
      settledRaceStandingsRef.current = startingRaceStandings;
      setResult(null);
      setErrorMessage("");
      setChatOpen(false);
      setChatMessages([]);
      setChatInput("");
      setChatUnreadCount(0);
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
    socket.on(ServerEvent.PLAYER_STATE, (state) => {
      setHelps(state.helps);
    });
    socket.on(ServerEvent.QUESTION, (nextQuestion) => {
      stopManagedSound("call_friend");
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
    socket.on(ServerEvent.ANSWER_RECEIVED, (answer) => {
      setSelectedOption(answer.selectedOption);
      setLockedAnswer(true);
    });
    socket.on(ServerEvent.SOUND_EFFECT, playSoundEffect);
    socket.on(ServerEvent.CHAT_NEW_MESSAGE, (message) => {
      const normalizedMessage = {
        ...message,
        is_own: message.is_own ?? message.user_id === socket.id,
      };
      setChatMessages((currentMessages) => [...currentMessages, normalizedMessage]);
      if (chatOpenRef.current) {
        scrollChatToBottom();
      }
    });
    socket.on(ServerEvent.CHAT_HISTORY, (messages) => {
      setChatMessages(messages);
      scrollChatToBottom();
    });
    socket.on(ServerEvent.CHAT_UNREAD_UPDATE, (update) => {
      setChatUnreadCount(update.unread_count || 0);
    });
    socket.on(ServerEvent.CHAT_HISTORY_CLEARED, () => {
      setChatMessages([]);
      setChatUnreadCount(0);
    });
    socket.on(ServerEvent.RACE_STANDINGS, (standings) => {
      setRaceStandings(standings || EMPTY_RACE_STANDINGS);
    });
    socket.on(ServerEvent.QUESTION_RESULT, (questionResult) => {
      const nextRaceStandings = questionResult.raceStandings || EMPTY_RACE_STANDINGS;

      stopManagedSound("ticking_clock");
      setPhase("result");
      setResult(questionResult);
      setLeaderboard(questionResult.leaderboard);
      setPreviousRaceStandings(settledRaceStandingsRef.current);
      setRaceStandings(nextRaceStandings);
      settledRaceStandingsRef.current = nextRaceStandings;
      setQuestionEndsAt(null);
      setTimeLeft(0);
      const currentPlayerResult = questionResult.answers.find(
        (answer) => answer.playerId === socket.id
      );
      if (!currentPlayerResult?.selectedOption) {
        playSoundEffect({ name: "no_answer" });
      } else {
        playSoundEffect({
          name: currentPlayerResult.isCorrect ? "correct_answer" : "wrong_answer",
        });
      }
    });
    socket.on(ServerEvent.HELP_USED, (helpResult) => {
      setHelps(helpResult.helps);
      if (helpResult.helpType === Lifeline.FIFTY_FIFTY) {
        setRemovedOptions(helpResult.removedOptions);
      }
      if (helpResult.helpType === Lifeline.DOUBLE_SCORE) {
        setDoubleScoreActive(Boolean(helpResult.doubleScoreActive));
      }
      if (helpResult.helpType === Lifeline.CALL_A_FRIEND) {
        stopManagedSound("call_friend");
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
    socket.on(ServerEvent.QUESTION_TIMER_PAUSED, (pauseInfo) => {
      stopManagedSound("ticking_clock");
      setTimeLeft(pauseInfo.secondsLeft);
      setQuestionEndsAt(null);
      if (pauseInfo.callerId === socket.id) {
        playManagedSound("call_friend");
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
    socket.on(ServerEvent.QUESTION_TIMER_RESUMED, (resumeInfo) => {
      stopManagedSound("call_friend");
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
    socket.on(ServerEvent.GAME_FINISHED, (summary) => {
      const finalRaceStandings = summary.raceStandings || EMPTY_RACE_STANDINGS;

      stopManagedSound("call_friend");
      stopManagedSound("ticking_clock");
      setPhase("finished");
      setLeaderboard(summary.leaderboard);
      setPreviousRaceStandings(settledRaceStandingsRef.current);
      setRaceStandings(finalRaceStandings);
      settledRaceStandingsRef.current = finalRaceStandings;
      setQuestion(null);
      setResult(null);
      setGameInfo(null);
      setQuestionEndsAt(null);
      setChatOpen(false);
      setChatMessages([]);
      setChatInput("");
      setChatUnreadCount(0);
      setFriendPopup({
        open: false,
        loading: false,
        message: "",
        confidence: null,
        friendAnswered: null,
        kind: "",
      });
    });
    socket.on(ServerEvent.ERROR_MESSAGE, (error) => {
      stopManagedSound("call_friend");
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
      stopManagedSound("call_friend");
      stopManagedSound("ticking_clock");
      socket.disconnect();
    };
  }, [
    ensureSoundAudio,
    playManagedSound,
    playSoundEffect,
    scrollChatToBottom,
    stopManagedSound,
  ]);

  useEffect(() => {
    if (!questionEndsAt) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      setTimeLeft(Math.max(0, Math.ceil((questionEndsAt - Date.now()) / 1000)));
    }, 250);

    return () => window.clearInterval(timer);
  }, [questionEndsAt]);

  useEffect(() => {
    if (phase !== "game" || !questionEndsAt) {
      stopManagedSound("ticking_clock");
      return undefined;
    }

    playManagedSound("ticking_clock", { loop: true });
    return () => stopManagedSound("ticking_clock");
  }, [phase, questionEndsAt, playManagedSound, stopManagedSound]);

  function joinQueue(event, profile = {}) {
    event.preventDefault();
    primeSoundEffects();
    const trimmedPlayerName = playerName.trim();
    setErrorMessage("");
    setPhase("waiting");
    setWaiting({
      secondsLeft: config.matchmakingSeconds,
      playerCount: 1,
      players: [trimmedPlayerName],
      playerProfiles: [
        {
          id: socketRef.current?.id || currentPlayerId || "current-player",
          name: trimmedPlayerName,
          ride: profile.ride,
          paint: profile.paint,
        },
      ],
    });
    socketRef.current?.emit(ClientEvent.JOIN_QUEUE, {
      name: playerName,
      ride: profile.ride,
      paint: profile.paint,
    });
  }

  function leaveLobby() {
    socketRef.current?.emit(ClientEvent.LEAVE_QUEUE);
    gameCountdownPlayedRef.current = false;
    setErrorMessage("");
    setWaiting({
      secondsLeft: config.matchmakingSeconds,
      playerCount: 0,
      players: [],
      playerProfiles: [],
    });
    setPhase("intro");
  }

  function chooseAnswer(option) {
    if (!question || lockedAnswer || removedOptions.includes(option)) {
      return;
    }

    playSoundEffect({ name: "click_possible_answer" });
    setSelectedOption(option);
    setLockedAnswer(true);
    socketRef.current?.emit(ClientEvent.ANSWER, {
      questionId: question.id,
      option,
    });
  }

  function useHelp(helpType) {
    if (!question || lockedAnswer) {
      return;
    }

    playSoundEffect({ name: "click" });
    setErrorMessage("");
    if (helpType === Lifeline.CALL_A_FRIEND) {
      setFriendPopup({
        open: true,
        loading: true,
        message: "Calling your funniest friend...",
        confidence: null,
        friendAnswered: null,
        kind: "caller_loading",
      });
    }
    socketRef.current?.emit(ClientEvent.USE_HELP, {
      questionId: question.id,
      helpType,
    });
  }

  function openChat() {
    if (!gameInfo?.gameId) {
      return;
    }

    setChatOpen(true);
    setChatUnreadCount(0);
    socketRef.current?.emit(ClientEvent.CHAT_REQUEST_HISTORY, { game_id: gameInfo.gameId });
    socketRef.current?.emit(ClientEvent.CHAT_OPEN, { game_id: gameInfo.gameId });
    scrollChatToBottom();
  }

  function closeChat() {
    setChatOpen(false);
  }

  function sendChatMessage(event) {
    event.preventDefault();
    const content = chatInput.trim();

    if (!content || !gameInfo?.gameId) {
      return;
    }

    socketRef.current?.emit(ClientEvent.CHAT_SEND_MESSAGE, {
      game_id: gameInfo.gameId,
      content,
    });
    setChatInput("");
  }

  const activeRaceStandings =
    raceStandings?.players?.length > 0
      ? raceStandings
      : gameInfo?.raceStandings || EMPTY_RACE_STANDINGS;

  if (phase === "intro") {
    return (
      <WelcomePage
        errorMessage={errorMessage}
        onPlayerNameChange={setPlayerName}
        onStart={joinQueue}
        playerName={playerName}
      />
    );
  }

  if (phase === "waiting") {
    return (
      <MatchmakingPage
        currentPlayerId={currentPlayerId}
        errorMessage={errorMessage}
        matchmakingSeconds={config.matchmakingSeconds}
        onLeave={leaveLobby}
        waiting={waiting}
      />
    );
  }

  return (
    <GamePage
      chatInput={chatInput}
      chatListRef={chatListRef}
      chatMessages={chatMessages}
      chatOpen={chatOpen}
      chatUnreadCount={chatUnreadCount}
      config={config}
      connectionStatus={connectionStatus}
      currentPlayerId={currentPlayerId}
      doubleScoreActive={doubleScoreActive}
      errorMessage={errorMessage}
      friendPopup={friendPopup}
      gameInfo={gameInfo}
      helps={helps}
      leaderboard={leaderboard}
      lockedAnswer={lockedAnswer}
      onChatInputChange={setChatInput}
      onChooseAnswer={chooseAnswer}
      onCloseChat={closeChat}
      onCloseFriendPopup={() =>
        setFriendPopup({
          open: false,
          loading: false,
          message: "",
          confidence: null,
          friendAnswered: null,
          kind: "",
        })
      }
      onOpenChat={openChat}
      onPlayAgain={() => {
        setRaceStandings(EMPTY_RACE_STANDINGS);
        setPreviousRaceStandings(EMPTY_RACE_STANDINGS);
        settledRaceStandingsRef.current = EMPTY_RACE_STANDINGS;
        setPhase("intro");
      }}
      onSendChatMessage={sendChatMessage}
      onUseHelp={useHelp}
      phase={phase}
      previousRaceStandings={previousRaceStandings}
      question={question}
      raceStandings={activeRaceStandings}
      removedOptions={removedOptions}
      result={result}
      selectedOption={selectedOption}
      timeLeft={timeLeft}
    />
  );
}
