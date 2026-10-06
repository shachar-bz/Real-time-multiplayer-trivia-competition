"use client";

import { useMemo } from "react";
import FinalLeaderboard from "@/components/results/FinalLeaderboard";
import RoundResult from "@/components/results/RoundResult";
import { cx } from "@/lib/classNames";
import { Phase } from "@/lib/gameReducer";
import ChatPanel from "./ChatPanel";
import FriendModal from "./FriendModal";
import QuestionStage from "./QuestionStage";
import RaceTrack from "./RaceTrack";
import styles from "./GameScreen.module.css";

/**
 * Everything after the lobby: the question, the round result or the final
 * board, with the friend popup, chat and race track layered on top.
 */
export default function GameScreen({
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
    phase === Phase.FINISHED
      ? "Final Lap"
      : `Round ${question?.index || 1}/${question?.total || config.questionsPerGame}`;

  const showRaceTrack =
    phase === Phase.GAME &&
    (raceStandings?.players?.length || 0) > 0;

  return (
    <main className={cx(styles.gameShell, phase === Phase.FINISHED ? styles.gameShellFinished : "")}>
      {phase !== Phase.FINISHED && <div className={styles.gameBackdrop} aria-hidden="true" />}

      {phase !== Phase.FINISHED && (
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

      {phase === Phase.GAME && question && (
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

      {phase === Phase.RESULT && result && (
        <RoundResult
          currentPlayerId={currentPlayerId}
          leaderboard={leaderboard}
          myResult={myResult}
          previousRaceStandings={previousRaceStandings}
          raceStandings={raceStandings}
          result={result}
        />
      )}

      {phase === Phase.FINISHED && (
        <FinalLeaderboard leaderboard={leaderboard} onBackToLobby={onPlayAgain} />
      )}

      {errorMessage && <p className={styles.error}>{errorMessage}</p>}

      {friendPopup.open && (
        <FriendModal friendPopup={friendPopup} onClose={onCloseFriendPopup} />
      )}

      {gameInfo && phase !== Phase.FINISHED && (
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
