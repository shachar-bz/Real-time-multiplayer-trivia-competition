"use client";

import { useMemo } from "react";
import FinalLeaderboardPage from "./final_leaderboard_page";
import ResultPage from "./result_page";
import { cx, paintFor, rideFor } from "@/lib/race";
import styles from "./game_page.module.css";

const HELP_FIFTY_FIFTY = "fifty_fifty";
const HELP_DOUBLE_SCORE = "double_score";
const HELP_CALL_A_FRIEND = "call_a_friend";
const FIXED_LANE_COUNT = 3;

export default function GamePage({
  chatInput,
  chatListRef,
  chatMessages,
  chatOpen,
  chatUnreadCount,
  config,
  connectionStatus,
  currentPlayerId,
  doubleScoreActive,
  errorMessage,
  friendPopup,
  gameInfo,
  helps,
  leaderboard,
  lockedAnswer,
  onChatInputChange,
  onChooseAnswer,
  onCloseChat,
  onCloseFriendPopup,
  onOpenChat,
  onPlayAgain,
  onSendChatMessage,
  onUseHelp,
  phase,
  previousRaceStandings,
  question,
  raceStandings,
  removedOptions,
  result,
  selectedOption,
  timeLeft,
}) {
  const myResult = useMemo(() => {
    if (!result || !currentPlayerId) {
      return null;
    }

    return result.answers.find((answer) => answer.playerId === currentPlayerId);
  }, [currentPlayerId, result]);

  const roundLabel =
    phase === "finished"
      ? "Final Lap"
      : `Round ${question?.index || 1}/${question?.total || config.questionsPerGame}`;

  const showRaceTrack =
    phase === "game" &&
    (raceStandings?.players?.length || 0) > 0;

  return (
    <main className={cx(styles.gameShell, phase === "finished" ? styles.gameShellFinished : "")}>
      {phase !== "finished" && <div className={styles.gameBackdrop} aria-hidden="true" />}

      {phase !== "finished" && (
        <header className={styles.gameTopbar} aria-label="Game status">
          <div className={styles.roundBadge}>{roundLabel}</div>
          <span
            className={cx(
              styles.status,
              connectionStatus === "Connected" ? styles.statusOnline : ""
            )}
          >
            {connectionStatus}
          </span>
        </header>
      )}

      {phase === "game" && question && (
        <QuestionStage
          doubleScoreActive={doubleScoreActive}
          friendPopup={friendPopup}
          helps={helps}
          lockedAnswer={lockedAnswer}
          onChooseAnswer={onChooseAnswer}
          onUseHelp={onUseHelp}
          question={question}
          removedOptions={removedOptions}
          selectedOption={selectedOption}
          timeLeft={timeLeft}
        />
      )}

      {phase === "result" && result && (
        <ResultPage
          currentPlayerId={currentPlayerId}
          leaderboard={leaderboard}
          myResult={myResult}
          previousRaceStandings={previousRaceStandings}
          raceStandings={raceStandings}
          result={result}
        />
      )}

      {phase === "finished" && (
        <FinalLeaderboardPage leaderboard={leaderboard} onBackToLobby={onPlayAgain} />
      )}

      {errorMessage && <p className={styles.error}>{errorMessage}</p>}

      {friendPopup.open && (
        <FriendModal friendPopup={friendPopup} onClose={onCloseFriendPopup} />
      )}

      {gameInfo && phase !== "finished" && (
        <ChatPanel
          chatInput={chatInput}
          chatListRef={chatListRef}
          chatMessages={chatMessages}
          chatOpen={chatOpen}
          chatUnreadCount={chatUnreadCount}
          onChatInputChange={onChatInputChange}
          onCloseChat={onCloseChat}
          onOpenChat={onOpenChat}
          onSendChatMessage={onSendChatMessage}
        />
      )}

      {showRaceTrack && (
        <RaceTrack currentPlayerId={currentPlayerId} standings={raceStandings} />
      )}
    </main>
  );
}

function QuestionStage({
  doubleScoreActive,
  friendPopup,
  helps,
  lockedAnswer,
  onChooseAnswer,
  onUseHelp,
  question,
  removedOptions,
  selectedOption,
  timeLeft,
}) {
  const timerTotal = Math.max(1, Number(question.seconds) || 20);
  const timerRatio = Math.max(0, Math.min(1, Number(timeLeft) / timerTotal));

  return (
    <section className={styles.playArea} aria-label="Question">
      <div className={styles.powerUps} aria-label="Question helps">
        <button
          aria-label="Use fifty fifty"
          className={styles.helpFifty}
          disabled={!helps.fiftyFifty || lockedAnswer || removedOptions.length > 0}
          onClick={() => onUseHelp(HELP_FIFTY_FIFTY)}
          type="button"
        >
          50/50
        </button>
        <button
          aria-label="Call a friend"
          className={styles.helpCall}
          disabled={!helps.callFriend || lockedAnswer || friendPopup.loading}
          onClick={() => onUseHelp(HELP_CALL_A_FRIEND)}
          type="button"
        >
          <span className={styles.callGlyph} aria-hidden="true" />
        </button>
        <div
          className={styles.timerGauge}
          style={{ "--timer-progress": `${timerRatio * 360}deg` }}
          aria-label={`${timeLeft} seconds left`}
        >
          <div className={styles.timerFace}>
            <strong>{String(timeLeft).padStart(2, "0")}</strong>
            <span>Sec</span>
          </div>
        </div>
        <button
          aria-label="Use double score"
          className={cx(styles.helpDouble, doubleScoreActive ? styles.helpActive : "")}
          disabled={!helps.doubleScore || lockedAnswer || doubleScoreActive}
          onClick={() => onUseHelp(HELP_DOUBLE_SCORE)}
          type="button"
        >
          X2
        </button>
      </div>

      <article className={styles.questionCard}>
        <p className={styles.questionMeta}>
          {question.topic} - Difficulty {question.difficulty}
        </p>
        <h1>{question.text}</h1>
      </article>

      <div className={styles.options} aria-label="Answer options">
        {question.options.map((option) => {
          const isSelected = selectedOption === option.key;
          const isRemoved = removedOptions.includes(option.key);

          return (
            <button
              className={cx(
                styles.option,
                isSelected ? styles.optionSelected : "",
                isRemoved ? styles.optionRemoved : ""
              )}
              disabled={lockedAnswer || isRemoved}
              key={option.key}
              onClick={() => onChooseAnswer(option.key)}
              type="button"
            >
              <strong>{option.key}</strong>
              <span>{option.text}</span>
            </button>
          );
        })}
      </div>

      <div className={styles.playStatus} aria-live="polite">
        {doubleScoreActive && <span>Double score armed</span>}
        {lockedAnswer && <span>Answer locked</span>}
      </div>
    </section>
  );
}

function FriendModal({ friendPopup, onClose }) {
  return (
    <div className={styles.modalBackdrop} role="presentation">
      <section className={styles.modal} aria-label="Call a friend message">
        <p className={styles.eyebrow}>Call a Friend</p>
        <p className={friendPopup.loading ? styles.muted : styles.friendMessage}>
          {friendPopup.message}
        </p>
        <button
          className={styles.secondaryButton}
          disabled={friendPopup.loading}
          onClick={onClose}
          type="button"
        >
          Close
        </button>
      </section>
    </div>
  );
}

function ChatPanel({
  chatInput,
  chatListRef,
  chatMessages,
  chatOpen,
  chatUnreadCount,
  onChatInputChange,
  onCloseChat,
  onOpenChat,
  onSendChatMessage,
}) {
  if (!chatOpen) {
    return (
      <aside className={styles.chatDock} aria-label="Game chat">
        <button className={styles.chatToggle} onClick={onOpenChat} type="button" aria-label="Open chat">
          <span className={styles.chatGlyph} aria-hidden="true" />
          {chatUnreadCount > 0 && <span className={styles.chatBadge}>{chatUnreadCount}</span>}
        </button>
      </aside>
    );
  }

  return (
    <aside className={cx(styles.chatDock, styles.chatOpen)} aria-label="Game chat">
      <div className={styles.chatHeader}>
        <strong>Chat</strong>
        <button className={styles.chatClose} onClick={onCloseChat} type="button" aria-label="Close chat">
          x
        </button>
      </div>
      <div className={styles.chatMessages} ref={chatListRef}>
        {chatMessages.map((message) => (
          <article
            className={cx(styles.chatMessage, message.is_own ? styles.chatMessageOwn : "")}
            key={message.id}
          >
            <span className={styles.chatUsername}>{message.username}</span>
            <p>{message.content}</p>
            <time>{message.timestamp}</time>
          </article>
        ))}
      </div>
      <form className={styles.chatForm} onSubmit={onSendChatMessage}>
        <input
          aria-label="Chat message"
          maxLength={240}
          onChange={(event) => onChatInputChange(event.target.value)}
          placeholder="Type a message"
          value={chatInput}
        />
        <button type="submit">Send</button>
      </form>
    </aside>
  );
}

function RaceTrack({ currentPlayerId, standings }) {
  const lanes = useMemo(() => fixedLanePlayers(standings), [standings]);

  return (
    <section className={styles.raceTrack} aria-label="Live race standings">
      <div className={styles.raceHeader}>
        <h2>Player Lanes</h2>
        <div className={styles.finishLabel}>
          <span aria-hidden="true">|&gt;</span>
          <span>Finish Line</span>
        </div>
      </div>
      <div className={styles.trackLanes}>
        <div className={styles.finishLine} aria-hidden="true" />
        {lanes.map((player, index) =>
          player ? (
            <RaceLane
              currentPlayerId={currentPlayerId}
              key={player.id || `${player.name}-${index}`}
              player={player}
            />
          ) : (
            <EmptyLane key={`empty-lane-${index}`} />
          )
        )}
      </div>
    </section>
  );
}

function fixedLanePlayers(standings) {
  const players = [...(standings?.players || [])];

  return Array.from({ length: FIXED_LANE_COUNT }, (_, index) => players[index] || null);
}

function RaceLane({ currentPlayerId, player }) {
  const progressPercent = 0;
  const vehicleLeft = "5%";
  const isCurrentPlayer = player.id === currentPlayerId;
  const ride = rideFor(player);
  const paint = paintFor(player);
  const laneColor = paint.hex || player.paintHex || "#00d2fd";
  const displayName = isCurrentPlayer ? "YOU" : player.name;

  return (
    <div className={cx(styles.raceLane, isCurrentPlayer ? styles.raceLaneCurrent : "")}>
      <span className={styles.laneProgress} style={{ width: `${progressPercent}%` }} />
      <div className={styles.laneVehicle} style={{ "--vehicle-left": vehicleLeft, "--lane-color": laneColor }}>
        <span className={styles.racerName}>{displayName}</span>
        <span className={styles.vehicleBadge} title={`${ride.name} - ${paint.name}`}>
          <img src={ride.image} alt={`${ride.name} selected by ${displayName}`} />
        </span>
        <span className={styles.laneScore}>{player.score} pts</span>
      </div>
    </div>
  );
}

function EmptyLane() {
  return (
    <div className={cx(styles.raceLane, styles.raceLaneEmpty)}>
      <span>Open Lane</span>
    </div>
  );
}
