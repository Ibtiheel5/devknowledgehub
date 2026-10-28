import { Button } from "../ui";
import styles from "./Topbar.module.css";

export function Topbar({
  title,
  subtitle,
  breadcrumbs,
  actions,
  onRefresh,
  refreshing = false
}) {
  return (
    <header className={styles.topbar}>
      <div className={styles.main}>
        <div className={styles.heading}>
          {breadcrumbs && <nav className={styles.breadcrumbs}>{breadcrumbs}</nav>}
          <h1 className={styles.title}>{title}</h1>
          {subtitle && <p className={styles.subtitle}>{subtitle}</p>}
        </div>
        <div className={styles.actions}>
          {actions}
          {onRefresh && (
            <Button
              variant="outline"
              onClick={onRefresh}
              disabled={refreshing}
              loading={refreshing}
            >
              Actualiser
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
