"use client";

import styles from "./GameScreen.module.css";

/** Call-a-friend popup: "calling..." while loading, then the friend's answer. */
export default function FriendModal({ friendPopup, onClose }) {
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
