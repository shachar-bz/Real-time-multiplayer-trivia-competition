"use client";

import { useMemo, useState } from "react";
import styles from "./welcome_page.module.css";

const PAINT_COLORS = [
  { id: "red", name: "Red", hex: "#d91400", glow: "rgba(217, 20, 0, 0.55)" },
  { id: "pink", name: "Pink", hex: "#ffb4a6", glow: "rgba(255, 180, 166, 0.55)" },
  { id: "yellow", name: "Yellow", hex: "#f6c400", glow: "rgba(246, 196, 0, 0.55)" },
  { id: "blue", name: "Blue", hex: "#8fe8ff", glow: "rgba(143, 232, 255, 0.6)" },
  { id: "white", name: "White", hex: "#e8e7f2", glow: "rgba(232, 231, 242, 0.45)" },
];

const RIDES = [
  {
    id: "motorcycle",
    name: "Motorcycle",
    defaultPaint: "blue",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuCr93Ha5S2_8RaAL98p-hYiWRlG4DRWzDoNsPHV7wms7LpNsIRSolbxEkkTY7IS4wFm6Or1eMnj-fWtgn11jTdvRzuqVP2YDCF45NNtzZtPJgP81ixpF3Rky0-DsCvz6C_a6BBJCRmsifxID4Tpictvio_gtuKUMeMG6Ay46Q7_2lxXKSHIdDjU4PO2ZldE-0b78Aw6uCX0qA8kLpQSvwrnsqcUj3yUS99hf5_n-hb5M_ol6kjumM2-UoBRt6-SfW2fl3yw5PkwNCOI",
    alt: "A sleek racing motorcycle on a night track.",
  },
  {
    id: "monster-truck",
    name: "Monster Truck",
    defaultPaint: "red",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuCWZbuF4hZ6he0S7J3SF7Tlwd9XAlwqF0t9wnoEBCPBP1Zp181yn6tNW6Ati_3yYWiU6adx7-cvNRnUGzKQ07VN2-Vv65o1da8ZjH_AafoRq6DkBQuOQdycVG5YV820Js2YbkEO2LswXf9EiL5Zbr-LsBQW1y3KwbcR_EynHcvTwWl1uJNtAEOM1G8coww0PIyhpNFwGq183d3uKQXBLBVUw6fEVwS5GNJYTaU2dHOyvOnAJoXhLwxR5AtKWm3QvqC83CeCaNOxC8xU",
    alt: "A monster truck with oversized tires in a stadium.",
  },
  {
    id: "sports-car",
    name: "Sports Car",
    defaultPaint: "white",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuAI1-MoRsSLqeh2pPGwcLi1OWJOZNaQRHg68LAiAlVITcEjVK9TzqVtEBacyAo42CLb8R-58aWAXMHHujPyZmvt4Hr0lvycRX82bT704_ZevsDYTxbi_ONoWRx3CTFcLvDTWHwagXPShfdF7l-HlvMNIZnpdQnoEPyOt1JgWZIqDzVW39SLJKxiqH_EssxUPDiFj9PoP0A_qsJo5461dnmyoMNxOdWOKnHUiUrvL17JL_Bec8PBsHno_mPwO1laMQNFypQPPZ22u_A2",
    alt: "A low sports car speeding through a dark track.",
  },
  {
    id: "superbike",
    name: "Superbike",
    defaultPaint: "yellow",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuCXgZ-pJYJOey9zwpU9q4tVaO9hOLVgauoWj4qwDFF4QZtIEZHEbq2u-XVwO1LOYPegPp7NXWRz3LIg7IqmVht-o-QRKg6JCUkbMBFYM41gZGXNaQREek8TgAANwTZ6KzndvcwG1tIhWuCsdd_8tWHI0jEbS13Lfnf8ZalLMsHlVJeJEi46J_r7cWOEEkmtR9fvMeKA4nw34UwZsr-Uq4cNbaehce3wV95l-Xh23W4a5D5GM7SKeMUagXwAFHD-lHlAmW_gdd0fWEUi",
    alt: "A sharp superbike angled for a high-speed turn.",
  },
];

const DEFAULT_PAINT_BY_RIDE = RIDES.reduce((paintMap, ride) => {
  paintMap[ride.id] = ride.defaultPaint;
  return paintMap;
}, {});

export default function WelcomePage({
  errorMessage,
  onPlayerNameChange,
  onStart,
  playerName,
}) {
  const [selectedRideId, setSelectedRideId] = useState("monster-truck");
  const [paintByRide, setPaintByRide] = useState(DEFAULT_PAINT_BY_RIDE);

  const selectedRide = useMemo(
    () => RIDES.find((ride) => ride.id === selectedRideId) || RIDES[0],
    [selectedRideId]
  );
  const selectedPaint = useMemo(
    () => PAINT_COLORS.find((paint) => paint.id === paintByRide[selectedRide.id]) || PAINT_COLORS[0],
    [paintByRide, selectedRide.id]
  );

  function choosePaint(rideId, paintId) {
    setPaintByRide((currentPaints) => ({
      ...currentPaints,
      [rideId]: paintId,
    }));
  }

  function startRace(event) {
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

      <form className={styles.trackCanvas} onSubmit={startRace}>
        <section className={styles.racerPanel} aria-label="Racer setup">
          <label className={styles.inputLabel} htmlFor="playerName">
            Enter Your Racer Name
          </label>
          <input
            autoComplete="nickname"
            className={styles.nameInput}
            id="playerName"
            maxLength={24}
            onChange={(event) => onPlayerNameChange(event.target.value)}
            placeholder="Player 1"
            value={playerName}
          />
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
                    onClick={() => setSelectedRideId(ride.id)}
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
          <button className={styles.startButton} type="submit">
            Start Race
          </button>
          {errorMessage && <p className={styles.errorMessage}>{errorMessage}</p>}
        </section>
      </form>
    </main>
  );
}
