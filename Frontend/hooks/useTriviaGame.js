import { useCallback, useEffect, useReducer, useRef } from "react";
import { io } from "socket.io-client";
import { GAME_COUNTDOWN_SECONDS, SERVER_URL } from "@/lib/config";
import {
  ActionType,
  Phase,
  canChooseAnswer,
  canUseHelp,
  gameReducer,
  initialState,
  secondsUntil,
  selectRaceStandings,
} from "@/lib/gameReducer";
import { ClientEvent, Lifeline, ServerEvent } from "@/lib/protocol";
import { roundResultSound } from "@/lib/sounds";
import { useSoundEffects } from "@/hooks/useSoundEffects";

/**
 * The client side of a trivia race, in one hook.
 *
 * It owns the Socket.IO connection, feeds every server event into the pure
 * game reducer (lib/gameReducer.js), and performs the side effects that go
 * with the state: sounds, the question clock, chat scrolling and the
 * messages sent back to the server.
 *
 * Returns:
 *   state          the reducer state (see initialState in lib/gameReducer.js)
 *   raceStandings  what the race track shows: live standings or the starting grid
 *   chatListRef    attach to the chat message list so it can scroll to the newest message
 *   actions        what the screens can do; each updates state and emits if needed
 */
export function useTriviaGame() {
  const [state, dispatch] = useReducer(gameReducer, initialState);
  const { playSoundEffect, playManagedSound, stopManagedSound, primeSoundEffects } =
    useSoundEffects();
  const socketRef = useRef(null);
  const gameCountdownPlayedRef = useRef(false);
  const chatListRef = useRef(null);
  const chatOpenRef = useRef(false);
  const { chatOpen, phase, questionEndsAt } = state;

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

  useEffect(() => {
    const socket = io(SERVER_URL, {
      autoConnect: true,
      transports: ["websocket", "polling"],
    });
    socketRef.current = socket;

    socket.on("connect", () => {
      dispatch({ type: ActionType.SOCKET_CONNECTED, socketId: socket.id });
    });
    socket.on("disconnect", () => dispatch({ type: ActionType.SOCKET_DISCONNECTED }));

    // Every server event updates the game state...
    Object.values(ServerEvent).forEach((event) => {
      socket.on(event, (payload) => {
        dispatch({ type: event, payload, selfId: socket.id, now: Date.now() });
      });
    });

    // ...and some also play or stop sounds, or scroll the chat.
    socket.on(ServerEvent.MATCHMAKING_STATUS, (status) => {
      // The countdown sound plays once per lobby countdown.
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
    socket.on(ServerEvent.GAME_STARTED, () => {
      stopManagedSound("call_friend");
      stopManagedSound("ticking_clock");
    });
    socket.on(ServerEvent.QUESTION, () => {
      stopManagedSound("call_friend");
    });
    socket.on(ServerEvent.SOUND_EFFECT, playSoundEffect);
    socket.on(ServerEvent.CHAT_NEW_MESSAGE, () => {
      if (chatOpenRef.current) {
        scrollChatToBottom();
      }
    });
    socket.on(ServerEvent.CHAT_HISTORY, () => {
      scrollChatToBottom();
    });
    socket.on(ServerEvent.QUESTION_RESULT, (questionResult) => {
      stopManagedSound("ticking_clock");
      playSoundEffect({ name: roundResultSound(questionResult, socket.id) });
    });
    socket.on(ServerEvent.HELP_USED, (helpResult) => {
      if (helpResult.helpType === Lifeline.CALL_A_FRIEND) {
        stopManagedSound("call_friend");
      }
    });
    socket.on(ServerEvent.QUESTION_TIMER_PAUSED, (pauseInfo) => {
      stopManagedSound("ticking_clock");
      if (pauseInfo.callerId === socket.id) {
        playManagedSound("call_friend");
      }
    });
    socket.on(ServerEvent.QUESTION_TIMER_RESUMED, () => {
      stopManagedSound("call_friend");
    });
    socket.on(ServerEvent.GAME_FINISHED, () => {
      stopManagedSound("call_friend");
      stopManagedSound("ticking_clock");
    });
    socket.on(ServerEvent.ERROR_MESSAGE, () => {
      stopManagedSound("call_friend");
    });

    return () => {
      stopManagedSound("call_friend");
      stopManagedSound("ticking_clock");
      socket.disconnect();
    };
  }, [
    playManagedSound,
    playSoundEffect,
    scrollChatToBottom,
    stopManagedSound,
  ]);

  // The question clock: recount the seconds left four times a second while it runs.
  useEffect(() => {
    if (!questionEndsAt) {
      return undefined;
    }

    const timer = window.setInterval(() => {
      dispatch({
        type: ActionType.CLOCK_TICKED,
        secondsLeft: secondsUntil(questionEndsAt, Date.now()),
      });
    }, 250);

    return () => window.clearInterval(timer);
  }, [questionEndsAt]);

  // The ticking-clock loop plays exactly while a question's clock is running.
  useEffect(() => {
    if (phase !== Phase.GAME || !questionEndsAt) {
      stopManagedSound("ticking_clock");
      return undefined;
    }

    playManagedSound("ticking_clock", { loop: true });
    return () => stopManagedSound("ticking_clock");
  }, [phase, questionEndsAt, playManagedSound, stopManagedSound]);

  function joinQueue(event, profile = {}) {
    event.preventDefault();
    primeSoundEffects();
    dispatch({ type: ActionType.QUEUE_JOINED, profile, socketId: socketRef.current?.id });
    socketRef.current?.emit(ClientEvent.JOIN_QUEUE, {
      name: state.playerName,
      ride: profile.ride,
      paint: profile.paint,
    });
  }

  function leaveLobby() {
    socketRef.current?.emit(ClientEvent.LEAVE_QUEUE);
    gameCountdownPlayedRef.current = false;
    dispatch({ type: ActionType.LOBBY_LEFT });
  }

  function chooseAnswer(option) {
    if (!canChooseAnswer(state, option)) {
      return;
    }

    playSoundEffect({ name: "click_possible_answer" });
    dispatch({ type: ActionType.ANSWER_CHOSEN, option });
    socketRef.current?.emit(ClientEvent.ANSWER, {
      questionId: state.question.id,
      option,
    });
  }

  function requestHelp(helpType) {
    if (!canUseHelp(state)) {
      return;
    }

    playSoundEffect({ name: "click" });
    dispatch({ type: ActionType.HELP_REQUESTED, helpType });
    socketRef.current?.emit(ClientEvent.USE_HELP, {
      questionId: state.question.id,
      helpType,
    });
  }

  function openChat() {
    const gameId = state.gameInfo?.gameId;
    if (!gameId) {
      return;
    }

    dispatch({ type: ActionType.CHAT_OPENED });
    socketRef.current?.emit(ClientEvent.CHAT_REQUEST_HISTORY, { game_id: gameId });
    socketRef.current?.emit(ClientEvent.CHAT_OPEN, { game_id: gameId });
    scrollChatToBottom();
  }

  function sendChatMessage(event) {
    event.preventDefault();
    const content = state.chatInput.trim();
    const gameId = state.gameInfo?.gameId;

    if (!content || !gameId) {
      return;
    }

    socketRef.current?.emit(ClientEvent.CHAT_SEND_MESSAGE, {
      game_id: gameId,
      content,
    });
    dispatch({ type: ActionType.CHAT_MESSAGE_SENT });
  }

  return {
    state,
    raceStandings: selectRaceStandings(state),
    chatListRef,
    actions: {
      setPlayerName: (name) => dispatch({ type: ActionType.PLAYER_NAME_CHANGED, name }),
      playClickSound: () => playSoundEffect({ name: "click" }),
      joinQueue,
      leaveLobby,
      chooseAnswer,
      requestHelp,
      closeFriendPopup: () => dispatch({ type: ActionType.FRIEND_POPUP_CLOSED }),
      openChat,
      closeChat: () => dispatch({ type: ActionType.CHAT_CLOSED }),
      setChatInput: (text) => dispatch({ type: ActionType.CHAT_INPUT_CHANGED, text }),
      sendChatMessage,
      playAgain: () => dispatch({ type: ActionType.PLAY_AGAIN }),
    },
  };
}
