import styles from "./Input.module.css";

export function TextField({
  label,
  hint,
  error,
  id,
  className,
  ...props
}) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={styles.field}>
      {label && (
        <label className={styles.label} htmlFor={inputId}>
          {label}
        </label>
      )}
      <input id={inputId} className={styles.input} {...props} />
      {error ? <span className={styles.error}>{error}</span> : hint && <span className={styles.hint}>{hint}</span>}
    </div>
  );
}

export function SearchInput({ className, ...props }) {
  return <input className={`${styles.input} ${styles.search} ${className || ""}`} type="search" {...props} />;
}

export function Select({ label, id, className, children, ...props }) {
  const inputId = id || label?.toLowerCase().replace(/\s+/g, "-");
  return (
    <div className={styles.field}>
      {label && (
        <label className={styles.label} htmlFor={inputId}>
          {label}
        </label>
      )}
      <select id={inputId} className={styles.select} {...props}>
        {children}
      </select>
    </div>
  );
}
