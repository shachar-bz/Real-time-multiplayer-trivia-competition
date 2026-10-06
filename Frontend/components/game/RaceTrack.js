"use client";

import { useMemo } from "react";
import { cx } from "@/lib/classNames";
import { paintFor, rideFor } from "@/lib/vehicles";
import styles from "./GameScreen.module.css";

const FIXED_LANE_COUNT = 3;

/** Live race lanes under the question: three fixed lanes for the first three racers in the standings. */
export default function RaceTrack({ currentPlayerId, standings }) {
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
