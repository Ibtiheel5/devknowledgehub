import { Outlet } from "react-router-dom";
import { useCallback, useEffect, useState } from "react";
import { Sidebar } from "./Sidebar";
import styles from "./AppLayout.module.css";
import { RepoProvider } from "../../store/RepoContext";
import { getHealth } from "../../services/graphApi";

export function AppLayout() {
  const [connection, setConnection] = useState({
    status: "loading",
    label: "Vérification de la connexion..."
  });

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

  return (
    <RepoProvider>
      <div className={styles.shell}>
        <Sidebar connection={connection} />
        <div className={styles.workspace}>
          <Outlet context={{ connection, refreshHealth }} />
        </div>
      </div>
    </RepoProvider>
  );
}
