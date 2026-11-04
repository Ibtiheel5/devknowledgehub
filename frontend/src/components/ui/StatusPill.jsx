import styles from "./StatusPill.module.css";

export function StatusPill({ status = "idle", label }) {
  return (
    <span className={`${styles.pill} ${styles[status]}`} role="status" aria-live="polite">
      <span className={styles.dot} aria-hidden="true" />
      {label}
    </span>
  );
}
