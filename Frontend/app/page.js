"use client";

import GameScreen from "@/components/game/GameScreen";
import MatchmakingScreen from "@/components/matchmaking/MatchmakingScreen";
import WelcomeScreen from "@/components/welcome/WelcomeScreen";
import { Phase } from "@/lib/gameReducer";
import { useTriviaGame } from "@/hooks/useTriviaGame";

/** The app's only route: shows the screen for the current game phase. */
export default function Home() {
  const { state, raceStandings, chatListRef, actions } = useTriviaGame();

  if (state.phase === Phase.INTRO) {
    return (
      <WelcomeScreen
        errorMessage={state.errorMessage}
        onPlayerNameChange={actions.setPlayerName}
        onStart={actions.joinQueue}
        playClickSound={actions.playClickSound}
        playerName={state.playerName}
      />
    );
  }

  if (state.phase === Phase.WAITING) {
    return (
      <MatchmakingScreen
        currentPlayerId={state.currentPlayerId}
        errorMessage={state.errorMessage}
        matchmakingSeconds={state.config.matchmakingSeconds}
        onLeave={actions.leaveLobby}
        waiting={state.waiting}
      />
    );
  }

  return (
    <GameScreen
      chatInput={state.chatInput}
      chatListRef={chatListRef}
      chatMessages={state.chatMessages}
      chatOpen={state.chatOpen}
      chatUnreadCount={state.chatUnreadCount}
      config={state.config}
      connectionStatus={state.connectionStatus}
      currentPlayerId={state.currentPlayerId}
      doubleScoreActive={state.doubleScoreActive}
      errorMessage={state.errorMessage}
      friendPopup={state.friendPopup}
      gameInfo={state.gameInfo}
      helps={state.helps}
      leaderboard={state.leaderboard}
      lockedAnswer={state.lockedAnswer}
      onChatInputChange={actions.setChatInput}
      onChooseAnswer={actions.chooseAnswer}
      onCloseChat={actions.closeChat}
      onCloseFriendPopup={actions.closeFriendPopup}
      onOpenChat={actions.openChat}
      onPlayAgain={actions.playAgain}
      onSendChatMessage={actions.sendChatMessage}
      onUseHelp={actions.requestHelp}
      phase={state.phase}
      previousRaceStandings={state.previousRaceStandings}
      question={state.question}
      raceStandings={raceStandings}
      removedOptions={state.removedOptions}
      result={state.result}
      selectedOption={state.selectedOption}
      timeLeft={state.timeLeft}
    />
  );
}
