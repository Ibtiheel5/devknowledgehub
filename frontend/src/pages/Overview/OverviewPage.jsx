import { useCallback, useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Topbar } from "../../components/layout";
import { Card, CardStat, DataTable, EmptyState, Button, SearchInput } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getRepoStats, getRepoSymbols, getRepoCalls } from "../../services/graphApi";
import { formatNumber, formatTime } from "../../utils/format";
import styles from "./OverviewPage.module.css";

export function OverviewPage() {
  const { connection, refreshHealth } = useOutletContext();
  const { activeRepo } = useRepo();
  const [stats, setStats] = useState(null);
  const [symbols, setSymbols] = useState([]);
  const [calls, setCalls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [nextStats, nextSymbols, nextCalls] = await Promise.all([
        getRepoStats(activeRepo),
        getRepoSymbols(activeRepo, 20),
        getRepoCalls(activeRepo, 50)
      ]);
      setStats(nextStats);
      setSymbols(Array.isArray(nextSymbols) ? nextSymbols : []);
      setCalls(Array.isArray(nextCalls) ? nextCalls : []);
      setUpdatedAt(new Date());
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const filteredSymbols = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return symbols.slice(0, 8);
    return symbols
      .filter((s) =>
        [s.qualified_name, s.name, s.file, s.kind]
          .filter(Boolean)
          .join(" ")
          .toLowerCase()
          .includes(query)
      )
      .slice(0, 8);
  }, [symbols, search]);

  const recentCalls = useMemo(() => calls.slice(0, 10), [calls]);

  return (
    <div className={styles.page}>
      <Topbar
        title="Vue d'ensemble"
        subtitle="Un aperçu synthétique du dépôt actif, de sa connectivité et de ses relations."
        breadcrumbs={<span>DevKnowledgeHub / Vue d'ensemble</span>}
        actions={
          <Button variant="subtle" as="a" href="/knowledge-graph">
            Ouvrir le graphe
          </Button>
        }
        onRefresh={async () => {
          await Promise.all([refreshHealth(), load()]);
        }}
        refreshing={loading}
      />

      <div className={styles.content}>
        <section className={styles.hero}>
          <Card>
            <div className={styles.heroGrid}>
              <div className={styles.heroInfo}>
                <span className={styles.kicker}>Dépôt actif</span>
                <h2 className={styles.heroTitle}>{activeRepo}</h2>
                <p className={styles.heroText}>
                  {error
                    ? error.message
                    : connection?.label ||
                      "Surveillez la santé du backend, des données Neo4j et l'évolution du graphe."}
                </p>
                <div className={styles.heroActions}>
                  <Button variant="primary" onClick={() => (window.location.href = "/repositories")}>
                    Gérer les dépôts
                  </Button>
                  <Button variant="outline" onClick={load}>
                    Relancer l'analyse
                  </Button>
                </div>
              </div>
              <div className={styles.heroStats}>
                <div className={styles.statTile}>
                  <span className={styles.statTileLabel}>Fichiers</span>
                  <span className={styles.statTileValue}>{formatNumber(stats?.files)}</span>
                </div>
                <div className={styles.statTile}>
                  <span className={styles.statTileLabel}>Symboles</span>
                  <span className={styles.statTileValue}>{formatNumber(stats?.symbols)}</span>
                </div>
                <div className={styles.statTile}>
                  <span className={styles.statTileLabel}>Appels</span>
                  <span className={styles.statTileValue}>{formatNumber(stats?.calls)}</span>
                </div>
                <div className={styles.statTile}>
                  <span className={styles.statTileLabel}>Imports</span>
                  <span className={styles.statTileValue}>{formatNumber(stats?.imports)}</span>
                </div>
              </div>
            </div>
            {updatedAt && (
              <span className={styles.updated}>Mis à jour à {formatTime(updatedAt)}</span>
            )}
          </Card>
        </section>

        <section className={styles.gridTwo}>
          <Card
            title="Points centraux"
            subtitle="Symboles les plus connectés"
            headerAction={
              <SearchInput
                placeholder="Filtrer..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            }
          >
            <DataTable
              columns={[
                { key: "qualified_name", label: "Symbole", render: (row) => (
                  <div className={styles.cellLine}>
                    <strong>{row.qualified_name ?? row.name}</strong>
                    <span>{row.kind ?? "symbole"} · {row.file}</span>
                  </div>
                )},
                { key: "degree", label: "Degré", align: "right", render: (row) => formatNumber(row.degree) }
              ]}
              data={filteredSymbols}
              emptyState={
                <EmptyState
                  title="Aucun symbole"
                  description="Construisez le graphe pour voir les points centraux."
                />
              }
            />
          </Card>

          <Card title="Appels récents" subtitle="10 premières relations">
            <DataTable
              columns={[
                { key: "caller", label: "Appelant", render: (row) => (
                  <div className={styles.cellLine}>
                    <strong>{row.caller}</strong>
                    {row.caller_kind && <span>{row.caller_kind}</span>}
                  </div>
                )},
                { key: "callee", label: "Appelé", render: (row) => (
                  <div className={styles.cellLine}>
                    <strong>{row.callee}</strong>
                    {row.callee_kind && <span>{row.callee_kind}</span>}
                  </div>
                )},
                { key: "line", label: "L", width: "60px", render: (row) => row.line ?? "—" }
              ]}
              data={recentCalls}
              emptyState={
                <EmptyState
                  title="Aucun appel"
                  description="Les appels apparaîtront après construction du graphe."
                />
              }
            />
          </Card>
        </section>
      </div>
    </div>
  );
}
