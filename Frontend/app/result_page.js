"use client";

import { useEffect, useMemo, useState } from "react";
import { cx } from "@/lib/classNames";
import { playersByScore, progressFor } from "@/lib/race";
import { paintFor, rideFor } from "@/lib/vehicles";
import styles from "./game_page.module.css";

function previousPlayerFor(player, previousPlayersById) {
  return previousPlayersById.get(player.id) || {
    ...player,
    progressRatio: 0,
    score: 0,
  };
}

function scoreLabel(score) {
  const safeScore = Number(score) || 0;
  return `${safeScore} pt${safeScore === 1 ? "" : "s"}`;
}

export default function ResultPage({
  currentPlayerId,
  leaderboard,
  myResult,
  previousRaceStandings,
  raceStandings,
  result,
}) {
  const [animateForward, setAnimateForward] = useState(false);
  const players = useMemo(
    () => playersByScore(raceStandings, leaderboard),
    [leaderboard, raceStandings]
  );
  const previousPlayersById = useMemo(
    () =>
      new Map(
        (previousRaceStandings?.players || []).map((player) => [player.id, player])
      ),
    [previousRaceStandings]
  );

  useEffect(() => {
    setAnimateForward(false);
    const animationFrame = window.requestAnimationFrame(() => {
      setAnimateForward(true);
    });

    return () => window.cancelAnimationFrame(animationFrame);
  }, [result.questionId]);

  return (
    <section className={cx(styles.panel, styles.resultPage)} aria-label="Round result">
      <div className={styles.resultAnswer}>
        <p className={styles.eyebrow}>Answer</p>
        <h2>
          Correct answer: {result.correctOption}. {result.correctAnswer}
        </h2>
        {myResult && (
          <p className={cx(styles.feedback, myResult.isCorrect ? styles.feedbackGood : styles.feedbackBad)}>
            {myResult.isCorrect
              ? `You got ${scoreLabel(myResult.pointsEarned)}.`
              : "No points this round."}
          </p>
        )}
      </div>

      <div className={styles.resultRace} aria-label="Result lanes">
        <div className={styles.resultRaceHeader}>
          <h3>Result Lanes</h3>
          <span>Highest score first</span>
        </div>
        <div className={styles.resultTrackLanes}>
          <div className={styles.resultFinishLine} aria-hidden="true" />
          {players.map((player) => (
            <ResultRaceLane
              animateForward={animateForward}
              currentPlayerId={currentPlayerId}
              key={player.id}
              player={player}
              previousPlayer={previousPlayerFor(player, previousPlayersById)}
              previousStandings={previousRaceStandings}
              standings={raceStandings}
            />
          ))}
        </div>
      </div>
    </section>
  );
}

function ResultRaceLane({
  animateForward,
  currentPlayerId,
  player,
  previousPlayer,
  previousStandings,
  standings,
}) {
  const startProgress = progressFor(previousPlayer, previousStandings);
  const endProgress = progressFor(player, standings);
  const progressRatio = animateForward ? endProgress : startProgress;
  const progressPercent = Math.round(progressRatio * 100);
  const vehicleLeft = `${5 + progressRatio * 86}%`;
  const isCurrentPlayer = player.id === currentPlayerId;
  const ride = rideFor(player);
  const paint = paintFor(player);
  const laneColor = paint.hex || player.paintHex || "#00d2fd";
  const displayName = isCurrentPlayer ? "YOU" : player.name;

  return (
    <div className={cx(styles.raceLane, styles.resultRaceLane, isCurrentPlayer ? styles.raceLaneCurrent : "")}>
      <span className={styles.laneProgress} style={{ width: `${progressPercent}%` }} />
      <div className={styles.laneVehicle} style={{ "--vehicle-left": vehicleLeft, "--lane-color": laneColor }}>
        <span className={styles.racerName}>{displayName}</span>
        <span className={styles.vehicleBadge} title={`${ride.name} - ${paint.name}`}>
          <img src={ride.image} alt={`${ride.name} selected by ${displayName}`} />
        </span>
        <span className={cx(styles.laneScore, styles.resultLaneScore)}>
          {scoreLabel(player.score)}
        </span>
      </div>
    </div>
  );
}
