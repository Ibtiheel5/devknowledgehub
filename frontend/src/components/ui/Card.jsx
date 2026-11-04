import styles from "./Card.module.css";

export function Card({
  title,
  subtitle,
  headerAction,
  children,
  className,
  footer,
  variant = "default"
}) {
  const classNames = [styles.card, variant === "outline" && styles.outline, className]
    .filter(Boolean)
    .join(" ");

  return (
    <article className={classNames}>
      {(title || subtitle || headerAction) && (
        <header className={styles.header}>
          <div className={styles.heading}>
            {title && <h2 className={styles.title}>{title}</h2>}
            {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
          </div>
          {headerAction && <div className={styles.action}>{headerAction}</div>}
        </header>
      )}
      <div className={styles.body}>{children}</div>
      {footer && <footer className={styles.footer}>{footer}</footer>}
    </article>
  );
}

export function CardStat({ label, value, icon, hint, trend }) {
  return (
    <div className={styles.stat}>
      <div className={styles.statTop}>
        {icon && <div className={styles.statIcon}>{icon}</div>}
        <span className={styles.statLabel}>{label}</span>
      </div>
      <div className={styles.statValue}>{value}</div>
      {hint && <span className={styles.statHint}>{hint}</span>}
      {trend && <span className={styles.statTrend}>{trend}</span>}
    </div>
  );
}
