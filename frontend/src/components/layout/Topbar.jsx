import { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import {
  Bell,
  ChevronDown,
  Menu,
  RefreshCw,
  Search,
  Settings,
  UserRound
} from "lucide-react";
import { Button } from "../ui";
import { useLayout } from "./LayoutContext";
import styles from "./Topbar.module.css";

export function Topbar({
  title,
  subtitle,
  breadcrumbs,
  actions,
  onRefresh,
  refreshing = false,
  showHeading = true
}) {
  const { openMobile, connection } = useLayout();
  const navigate = useNavigate();
  const location = useLocation();
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const menuRef = useRef(null);

  useEffect(() => {
    setMenuOpen(false);
    setNotificationsOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const onPointerDown = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
        setNotificationsOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, []);

  const notifications =
    connection?.status && connection.status !== "ok"
      ? [
          {
            id: "health",
            title: "Connexion backend dégradée",
            detail: connection.label,
            to: "/monitoring"
          }
        ]
      : [];

  const submitSearch = (event) => {
    event.preventDefault();
    const value = query.trim();
    navigate(value ? `/projects?search=${encodeURIComponent(value)}` : "/projects");
  };

  return (
    <header className={styles.topbar}>
      <div className={styles.utility}>
        <button
          type="button"
          className={styles.menuButton}
          onClick={openMobile}
          aria-label="Ouvrir la navigation"
        >
          <Menu size={20} />
        </button>

        <form className={styles.globalSearch} onSubmit={submitSearch} role="search">
          <Search size={16} aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Rechercher un projet, un ticket, un fichier..."
            aria-label="Recherche globale"
          />
          <kbd>↵</kbd>
        </form>

        <div className={styles.utilityActions} ref={menuRef}>
          <div className={styles.popoverWrap}>
            <button
              type="button"
              className={styles.iconAction}
              aria-label="Notifications"
              aria-expanded={notificationsOpen}
              onClick={() => {
                setNotificationsOpen((value) => !value);
                setMenuOpen(false);
              }}
            >
              <Bell size={18} />
              {notifications.length > 0 && (
                <span className={styles.badge}>{notifications.length}</span>
              )}
            </button>
            {notificationsOpen && (
              <div className={styles.popover} role="menu">
                <span className={styles.popoverTitle}>Notifications</span>
                {notifications.length === 0 ? (
                  <p className={styles.popoverEmpty}>Aucune alerte en cours.</p>
                ) : (
                  notifications.map((item) => (
                    <Link
                      key={item.id}
                      className={styles.notification}
                      to={item.to}
                      role="menuitem"
                    >
                      <strong>{item.title}</strong>
                      <span>{item.detail}</span>
                    </Link>
                  ))
                )}
              </div>
            )}
          </div>

          <div className={styles.popoverWrap}>
            <button
              type="button"
              className={styles.account}
              aria-label="Menu du compte"
              aria-expanded={menuOpen}
              onClick={() => {
                setMenuOpen((value) => !value);
                setNotificationsOpen(false);
              }}
            >
              <span className={styles.avatar}>DK</span>
              <span className={styles.accountText}>
                <strong>Utilisateur local</strong>
                <small>Session de développement</small>
              </span>
              <ChevronDown size={15} />
            </button>
            {menuOpen && (
              <div className={styles.popover} role="menu">
                <span className={styles.popoverTitle}>Compte</span>
                <Link className={styles.menuItem} to="/settings" role="menuitem">
                  <Settings size={16} />
                  Profil et préférences
                </Link>
                <Link className={styles.menuItem} to="/monitoring" role="menuitem">
                  <UserRound size={16} />
                  État du système
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {showHeading && (
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
                <RefreshCw size={15} />
                Actualiser
              </Button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
