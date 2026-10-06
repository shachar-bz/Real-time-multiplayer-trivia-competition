"use client";

import { useMemo } from "react";
import { cx } from "@/lib/classNames";
import { sortPlayersByScore } from "@/lib/race";
import { rideFor } from "@/lib/vehicles";
import styles from "./FinalLeaderboard.module.css";

const PODIUM_ORDER = [1, 0, 2];

function formatScore(score) {
  return (Number(score) || 0).toLocaleString("en-US");
}

function playerKey(player, rank) {
  return player?.id || `${player?.name || "racer"}-${rank}`;
}

export default function FinalLeaderboard({ leaderboard, onBackToLobby }) {
  const players = useMemo(() => sortPlayersByScore(leaderboard), [leaderboard]);
  const podiumPlayers = PODIUM_ORDER.map((playerIndex) => ({
    player: players[playerIndex],
    rank: playerIndex + 1,
  })).filter(({ player }) => player);
  const remainingPlayers = players.slice(3);
  const isScrollable = players.length > 6;

  return (
    <section className={styles.finalLeaderboard} aria-label="Final leaderboard">
      <div className={styles.speedLines} aria-hidden="true" />

      <div className={styles.boardContent}>
        <div className={styles.podium} aria-label="Top racers">
          {podiumPlayers.map(({ player, rank }) => (
            <PodiumCard key={playerKey(player, rank)} player={player} rank={rank} />
          ))}
        </div>

        <section className={styles.standingsCard} aria-label="Full standings">
          <div className={styles.standingsHeader}>
            <span>Rank</span>
            <span>Racer</span>
            <span>Points</span>
          </div>

          <ol
            className={cx(
              styles.standingsRows,
              isScrollable ? styles.standingsRowsScrollable : ""
            )}
          >
            {remainingPlayers.length > 0 ? (
              remainingPlayers.map((player, index) => {
                const rank = index + 4;

                return (
                  <li className={styles.standingsRow} key={playerKey(player, rank)}>
                    <span className={styles.rowRank}>{rank}</span>
                    <span className={styles.rowRacer}>
                      <span className={styles.racerGlyph} aria-hidden="true" />
                      <span className={styles.racerName}>
                        {player.name}
                        {!player.connected && <em>offline</em>}
                      </span>
                    </span>
                    <strong>{formatScore(player.score)}</strong>
                  </li>
                );
              })
            ) : (
              <li className={cx(styles.standingsRow, styles.emptyRow)}>
                <span className={styles.rowRank}>-</span>
                <span className={styles.rowRacer}>No additional racers</span>
                <strong>-</strong>
              </li>
            )}
          </ol>
        </section>

        <button className={styles.backButton} onClick={onBackToLobby} type="button">
          <span className={styles.flagIcon} aria-hidden="true" />
          <span>Back To Lobby</span>
        </button>
      </div>
    </section>
  );
}

function PodiumCard({ player, rank }) {
  const ride = rideFor(player);
  const rankClass =
    rank === 1
      ? styles.podiumFirst
      : rank === 2
        ? styles.podiumSecond
        : styles.podiumThird;

  return (
    <article className={cx(styles.podiumCard, rankClass)}>
      <span className={styles.podiumAvatar}>
        <img src={ride.image} alt={`${ride.name} selected by ${player.name}`} />
      </span>

      <h2>{player.name}</h2>

      <div className={styles.podiumBlock}>
        <span className={styles.blockGlow} aria-hidden="true" />
        <strong>{formatScore(player.score)}</strong>
        <span className={styles.pointsLabel}>Pts</span>
      </div>
    </article>
  );
}
