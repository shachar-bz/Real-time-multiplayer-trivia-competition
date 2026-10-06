"use client";

import { useMemo, useRef, useState } from "react";
import { PAINT_COLORS, RIDES } from "@/lib/vehicles";
import styles from "./welcome_page.module.css";

const DEFAULT_PAINT_BY_RIDE = RIDES.reduce((paintMap, ride) => {
  paintMap[ride.id] = ride.defaultPaint;
  return paintMap;
}, {});

export default function WelcomePage({
  errorMessage,
  onPlayerNameChange,
  onStart,
  playClickSound,
  playerName,
}) {
  const [selectedRideId, setSelectedRideId] = useState("monster-truck");
  const [paintByRide, setPaintByRide] = useState(DEFAULT_PAINT_BY_RIDE);
  const [nameError, setNameError] = useState("");
  const playerNameInputRef = useRef(null);

  const selectedRide = useMemo(
    () => RIDES.find((ride) => ride.id === selectedRideId) || RIDES[0],
    [selectedRideId]
  );
  const selectedPaint = useMemo(
    () => PAINT_COLORS.find((paint) => paint.id === paintByRide[selectedRide.id]) || PAINT_COLORS[0],
    [paintByRide, selectedRide.id]
  );

  function choosePaint(rideId, paintId) {
    playClickSound();
    setPaintByRide((currentPaints) => ({
      ...currentPaints,
      [rideId]: paintId,
    }));
  }

  function chooseRide(rideId) {
    playClickSound();
    setSelectedRideId(rideId);
  }

  function updatePlayerName(value) {
    if (nameError && value.trim()) {
      setNameError("");
    }

    onPlayerNameChange(value);
  }

  function startRace(event) {
    playClickSound();
    if (!playerName.trim()) {
      setNameError("Username is required to start the game.");
      playerNameInputRef.current?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
      playerNameInputRef.current?.focus({ preventScroll: true });
      return;
    }

    onStart(event, {
      ride: selectedRide.id,
      paint: selectedPaint.id,
    });
  }

  return (
    <main className={styles.welcomeShell}>
      <header className={styles.topBar}>
        <div className={styles.brand}>Nitro Trivia</div>
      </header>

      <div className={styles.trackCanvas}>
        <section className={styles.racerPanel} aria-label="Racer setup">
          <label className={styles.inputLabel} htmlFor="playerName">
            Enter Your Racer Name
          </label>
          <input
            autoComplete="nickname"
            className={styles.nameInput}
            id="playerName"
            maxLength={24}
            onClick={playClickSound}
            onChange={(event) => updatePlayerName(event.target.value)}
            placeholder="TYPE YOUR NAME"
            ref={playerNameInputRef}
            value={playerName}
          />
          {nameError && <p className={styles.nameError}>{nameError}</p>}
        </section>

        <section className={styles.heroHeader}>
          <h1>Pick Your Ride</h1>
          <p>Select your machine and customize your primary color to dominate the track.</p>
        </section>

        <section className={styles.rideGrid} aria-label="Ride selection">
          {RIDES.map((ride) => {
            const isSelectedRide = selectedRideId === ride.id;
            const activePaintId = paintByRide[ride.id];

            return (
              <article
                className={`${styles.rideCard} ${isSelectedRide ? styles.rideCardSelected : ""}`}
                key={ride.id}
              >
                <div className={styles.rideImageFrame}>
                  <img className={styles.rideImage} src={ride.image} alt={ride.alt} />
                </div>
                <div className={styles.rideDetails}>
                  <h2>{ride.name}</h2>
                  <div className={styles.paintSection}>
                    <span>Paint Job</span>
                    <div className={styles.paintRow}>
                      {PAINT_COLORS.map((paint) => {
                        const isSelectedPaint = activePaintId === paint.id;

                        return (
                          <button
                            aria-label={`${paint.name} paint for ${ride.name}`}
                            aria-pressed={isSelectedPaint}
                            className={`${styles.paintSwatch} ${
                              isSelectedPaint ? styles.paintSwatchSelected : ""
                            }`}
                            key={paint.id}
                            onClick={() => choosePaint(ride.id, paint.id)}
                            style={{
                              "--paint-color": paint.hex,
                              "--paint-glow": paint.glow,
                            }}
                            type="button"
                          />
                        );
                      })}
                    </div>
                  </div>
                  <button
                    aria-pressed={isSelectedRide}
                    className={`${styles.selectButton} ${
                      isSelectedRide ? styles.selectButtonSelected : ""
                    }`}
                    onClick={() => chooseRide(ride.id)}
                    type="button"
                  >
                    {isSelectedRide ? "Selected" : "Select"}
                  </button>
                </div>
              </article>
            );
          })}
        </section>

        <section className={styles.startDock} aria-label="Start race">
          <p className={styles.selectionSummary}>
            {selectedRide.name} / {selectedPaint.name}
          </p>
          <button className={styles.startButton} onClick={startRace} type="button">
            Start Race
          </button>
          {errorMessage && <p className={styles.errorMessage}>{errorMessage}</p>}
        </section>
      </div>
    </main>
  );
}
