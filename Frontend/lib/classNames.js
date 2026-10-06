/** Joins the truthy class names: cx(styles.lane, isCurrent && styles.current). */
export function cx(...classNames) {
  return classNames.filter(Boolean).join(" ");
}
