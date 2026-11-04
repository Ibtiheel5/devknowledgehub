import { Link, NavLink } from "react-router-dom";
import { ChevronsLeft, ChevronsRight, Plus, X } from "lucide-react";
import { useRepo } from "../../store/RepoContext";
import { StatusPill } from "../ui";
import { NavIcon } from "./NavIcon";
import { useLayout } from "./LayoutContext";
import styles from "./Sidebar.module.css";
import { navItems, secondaryItems } from "../../config/navigation";

export function Sidebar({ connection }) {
  const { activeRepo } = useRepo();
  const { collapsed, mobileOpen, toggleCollapsed, closeMobile } = useLayout();

  return (
    <aside
      className={`${styles.sidebar} ${collapsed ? styles.collapsed : ""} ${
        mobileOpen ? styles.mobileOpen : ""
      }`}
      aria-label="Navigation principale"
    >
      <div className={styles.brandRow}>
        <Link className={styles.brand} to="/" title="DevKnowledgeHub">
          <span className={styles.brandIcon} aria-hidden="true">
            DK
          </span>
          <span className={styles.brandText}>
            <span className={styles.brandTitle}>DevKnowledgeHub</span>
            <span className={styles.brandSub}>Intelligence logicielle</span>
          </span>
        </Link>
        <button
          type="button"
          className={styles.collapseButton}
          onClick={toggleCollapsed}
          aria-label={collapsed ? "Déplier la navigation" : "Replier la navigation"}
          title={collapsed ? "Déplier" : "Replier"}
        >
          {collapsed ? <ChevronsRight size={17} /> : <ChevronsLeft size={17} />}
        </button>
        <button
          type="button"
          className={styles.closeButton}
          onClick={closeMobile}
          aria-label="Fermer la navigation"
        >
          <X size={18} />
        </button>
      </div>

      <div className={styles.scroll}>
        <Link
          className={styles.importAction}
          to="/projects"
          title="Importer un dépôt"
          onClick={closeMobile}
        >
          <span className={styles.importIcon} aria-hidden="true">
            <Plus size={16} />
          </span>
          <span className={styles.importText}>
            <strong>Importer un dépôt</strong>
            <small>Commencer une analyse</small>
          </span>
        </Link>

        <nav className={styles.nav} aria-label="Navigation principale">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              title={item.label}
              onClick={closeMobile}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.active : ""}`
              }
            >
              <span className={styles.icon} aria-hidden="true">
                <NavIcon name={item.icon} />
              </span>
              <span className={styles.navLabel}>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        <div className={styles.secondary}>
          <span className={styles.groupLabel}>Outils</span>
          {secondaryItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              title={item.label}
              onClick={closeMobile}
              className={({ isActive }) =>
                `${styles.navLink} ${isActive ? styles.active : ""}`
              }
            >
              <span className={styles.icon} aria-hidden="true">
                <NavIcon name={item.icon} />
              </span>
              <span className={styles.navLabel}>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </div>

      <div className={styles.footer}>
        <div className={styles.repo}>
          <span className={styles.repoLabel}>Dépôt actif</span>
          <span className={styles.repoName} title={activeRepo}>
            {activeRepo}
          </span>
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
