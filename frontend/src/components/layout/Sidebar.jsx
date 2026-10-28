import { Link, NavLink } from "react-router-dom";
import { useRepo } from "../../store/RepoContext";
import { StatusPill } from "../ui";
import styles from "./Sidebar.module.css";
import { navItems } from "../../config/navigation";

export function Sidebar({ connection }) {
  const { activeRepo } = useRepo();

  return (
    <aside className={styles.sidebar} aria-label="Navigation principale">
      <Link className={styles.brand} to="/">
        <span className={styles.brandIcon} aria-hidden="true">
          DKH
        </span>
        <div className={styles.brandText}>
          <span className={styles.brandTitle}>DevKnowledgeHub</span>
          <span className={styles.brandSub}>Intelligence logicielle</span>
        </div>
      </Link>

      <div className={styles.section}>
        <span className={styles.label}>Espace de travail</span>
        <nav className={styles.nav}>
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.active : ""}`
              }
            >
              <span className={styles.icon}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      <div className={styles.footer}>
        <div className={styles.repo}>
          <span className={styles.repoLabel}>Dépôt actif</span>
          <span className={styles.repoName}>{activeRepo}</span>
        </div>
        {connection && (
          <StatusPill
            status={connection.status === "loading" ? "loading" : connection.status}
            label={connection.label}
          />
        )}
      </div>
    </aside>
  );
}
