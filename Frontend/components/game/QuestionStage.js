"use client";

import { cx } from "@/lib/classNames";
import { Lifeline } from "@/lib/protocol";
import styles from "./GameScreen.module.css";

/** The open question: lifeline buttons around the timer, the question card and the options. */
export default function QuestionStage({
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
          onClick={() => onUseHelp(Lifeline.FIFTY_FIFTY)}
          type="button"
        >
          50/50
        </button>
        <button
          aria-label="Call a friend"
          className={styles.helpCall}
          disabled={!helps.callFriend || lockedAnswer || friendPopup.loading}
          onClick={() => onUseHelp(Lifeline.CALL_A_FRIEND)}
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
          onClick={() => onUseHelp(Lifeline.DOUBLE_SCORE)}
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
