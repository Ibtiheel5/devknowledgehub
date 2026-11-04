import { Outlet, useLocation } from "react-router-dom";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Sidebar } from "./Sidebar";
import styles from "./AppLayout.module.css";
import { RepoProvider } from "../../store/RepoContext";
import { getHealth } from "../../services/graphApi";
import { LayoutContext } from "./LayoutContext";

const COLLAPSE_KEY = "dkh.sidebar-collapsed";

export function AppLayout() {
  const location = useLocation();
  const [connection, setConnection] = useState({
    status: "loading",
    label: "Vérification de la connexion..."
  });
  const [collapsed, setCollapsed] = useState(() => {
    try {
      return localStorage.getItem(COLLAPSE_KEY) === "1";
    } catch {
      return false;
    }
  });
  const [mobileOpen, setMobileOpen] = useState(false);

  const refreshHealth = useCallback(async () => {
    setConnection({ status: "loading", label: "Actualisation..." });
    try {
      const health = await getHealth();
      if (health?.api === "ok") {
        setConnection({
          status: health.neo4j ? "ok" : "warn",
          label: health.neo4j ? "API et Neo4j connectés" : "Neo4j indisponible"
        });
      } else {
        setConnection({ status: "error", label: "Réponse inattendue du backend" });
      }
    } catch (error) {
      setConnection({
        status: "error",
        label: error?.message || "Backend indisponible"
      });
    }
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  const toggleCollapsed = useCallback(() => {
    setCollapsed((value) => {
      const next = !value;
      try {
        localStorage.setItem(COLLAPSE_KEY, next ? "1" : "0");
      } catch {
        // stockage local indisponible : le choix reste en mémoire
      }
      return next;
    });
  }, []);

  const layoutValue = useMemo(
    () => ({
      collapsed,
      mobileOpen,
      connection,
      toggleCollapsed,
      openMobile: () => setMobileOpen(true),
      closeMobile: () => setMobileOpen(false)
    }),
    [collapsed, mobileOpen, connection, toggleCollapsed]
  );

  return (
    <RepoProvider>
      <LayoutContext.Provider value={layoutValue}>
        <div className={`${styles.shell} ${collapsed ? styles.collapsed : ""}`}>
          <Sidebar connection={connection} />
          {mobileOpen && (
            <button
              type="button"
              className={styles.overlay}
              aria-label="Fermer la navigation"
              onClick={() => setMobileOpen(false)}
            />
          )}
          <div className={styles.workspace}>
            <Outlet context={{ connection, refreshHealth }} />
          </div>
        </div>
      </LayoutContext.Provider>
    </RepoProvider>
  );
}
