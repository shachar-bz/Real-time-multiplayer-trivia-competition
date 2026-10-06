"use client";

import { useMemo } from "react";
import { paintFor, rideFor } from "@/lib/vehicles";
import styles from "./MatchmakingScreen.module.css";

const TARGET_GRID_SLOTS = 4;

function profileListFromWaiting(waiting) {
  if (Array.isArray(waiting?.playerProfiles) && waiting.playerProfiles.length > 0) {
    return waiting.playerProfiles;
  }

  return (waiting?.players || []).map((name, index) => ({
    id: `waiting-player-${index}`,
    name,
  }));
}

/** The lobby: countdown to the start and the starting grid of racers found so far. */
export default function MatchmakingScreen({
  currentPlayerId,
  errorMessage,
  matchmakingSeconds = 30,
  onLeave,
  waiting,
}) {
  const playerProfiles = useMemo(() => profileListFromWaiting(waiting), [waiting]);
  const countdownTotal = Math.max(1, Number(matchmakingSeconds) || 30);
  const receivedSecondsLeft = Number(waiting?.secondsLeft);
  const secondsLeft = Number.isFinite(receivedSecondsLeft)
    ? Math.max(0, receivedSecondsLeft)
    : countdownTotal;
  const racerCount = Math.max(Number(waiting?.playerCount) || 0, playerProfiles.length);
  const remainingRatio = Math.max(0, Math.min(1, secondsLeft / countdownTotal));
  const timerStyle = {
    "--timer-progress": `${remainingRatio * 360}deg`,
  };
  const slots =
    playerProfiles.length >= TARGET_GRID_SLOTS
      ? playerProfiles
      : [
          ...playerProfiles,
          ...Array.from({ length: TARGET_GRID_SLOTS - playerProfiles.length }, (_, index) => ({
            id: `searching-slot-${index}`,
            isPlaceholder: true,
          })),
        ];

  return (
    <main className={styles.matchmakingShell}>
      <header className={styles.brandBar} aria-label="Nitro Trivia">
        <span className={styles.brandText}>Nitro Trivia</span>
      </header>

      <section className={styles.timerSection} aria-label={`${secondsLeft} seconds to start`}>
        <div className={styles.timerGauge} style={timerStyle}>
          <div className={styles.timerFace}>
            <strong>{secondsLeft}</strong>
            <span>Sec to start</span>
          </div>
        </div>
      </section>

      <section className={styles.gridSection} aria-label="Starting grid">
        <div className={styles.gridHeader}>
          <h2>Starting Grid</h2>
          <span>
            {racerCount} Racer{racerCount === 1 ? "" : "s"}
          </span>
        </div>

        <div className={styles.gridList}>
          {slots.map((profile, index) =>
            profile.isPlaceholder ? (
              <SearchingSlot key={profile.id} />
            ) : (
              <RacerSlot
                currentPlayerId={currentPlayerId}
                index={index}
                key={profile.id || `${profile.name}-${index}`}
                profile={profile}
              />
            )
          )}
        </div>
      </section>

      <aside className={styles.botNote}>
        <span className={styles.botIcon} aria-hidden="true">
          <span />
        </span>
        <p>
          Not enough players? <strong>Nitro Bots</strong> will join the grid when the timer hits
          zero.
        </p>
      </aside>

      {errorMessage && <p className={styles.errorMessage}>{errorMessage}</p>}

      <button className={styles.leaveButton} onClick={onLeave} type="button">
        Leave Lobby
      </button>
    </main>
  );
}

function RacerSlot({ currentPlayerId, index, profile }) {
  const ride = rideFor(profile);
  const paint = paintFor(profile);
  const isCurrentPlayer = currentPlayerId ? profile.id === currentPlayerId : index === 0;
  const displayName = isCurrentPlayer ? "You" : profile.name || "Racer";
  const accentColor = profile.paintHex || paint.hex;

  return (
    <article
      className={`${styles.racerCard} ${isCurrentPlayer ? styles.racerCardCurrent : ""}`}
      style={{ "--slot-accent": accentColor }}
    >
      <div className={styles.vehicleFrame}>
        <img src={ride.image} alt={`${ride.name} selected by ${displayName}`} />
      </div>
      <h3>{displayName}</h3>
    </article>
  );
}

function SearchingSlot() {
  return (
    <article className={styles.searchingCard} aria-label="Searching for another racer">
      <span aria-hidden="true">+</span>
      <p>Searching...</p>
    </article>
  );
}
