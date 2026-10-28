import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useOutletContext, useSearchParams } from "react-router-dom";
import { Topbar } from "../../components/layout";
import { Card, CardStat, DataTable, EmptyState, SearchInput, Select } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { ForceGraph } from "../../components/graph";
import {
  getCallees,
  getCallers,
  getRepoCalls,
  getRepoStats,
  getRepoSymbols
} from "../../services/graphApi";
import { formatNumber, formatTime, pluralize } from "../../utils/format";
import styles from "./KnowledgeGraphPage.module.css";

export function KnowledgeGraphPage() {
  const { connection, refreshHealth } = useOutletContext();
  const { activeRepo } = useRepo();
  const [searchParams, setSearchParams] = useSearchParams();
  // Le symbole ciblé n'est lu qu'au montage : cliquer un nœud ne doit pas relancer le chargement.
  const focusRef = useRef(searchParams.get("focus"));
  const [selected, setSelected] = useState(focusRef.current);
  const [stats, setStats] = useState(null);
  const [calls, setCalls] = useState([]);
  const [symbols, setSymbols] = useState([]);
  const [search, setSearch] = useState("");
  const [callerKind, setCallerKind] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [nextStats, nextCalls, nextSymbols] = await Promise.all([
        getRepoStats(activeRepo),
        getRepoCalls(activeRepo, 200),
        getRepoSymbols(activeRepo, 50)
      ]);

      let merged = Array.isArray(nextCalls) ? [...nextCalls] : [];

      // Symbole ciblé (ex. depuis le Copilot) : on charge ses voisins même hors échantillon.
      const focus = focusRef.current;
      if (focus) {
        const [callers, callees] = await Promise.all([
          getCallers(activeRepo, focus).catch(() => []),
          getCallees(activeRepo, focus).catch(() => [])
        ]);
        for (const r of callers) {
          merged.push({ caller: r.qualified_name, caller_kind: r.kind, callee: focus, line: r.line });
        }
        for (const r of callees) {
          merged.push({ caller: focus, callee: r.qualified_name, callee_kind: r.kind, line: r.line });
        }
      }

      setStats(nextStats);
      setCalls(merged);
      setSymbols(Array.isArray(nextSymbols) ? nextSymbols : []);
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

  const kinds = useMemo(
    () => [...new Set(calls.map((call) => call.caller_kind).filter(Boolean))].sort(),
    [calls]
  );

  const filteredCalls = useMemo(() => {
    const query = search.trim().toLowerCase();
    return calls.filter((call) => {
      const matchesKind = callerKind === "all" || call.caller_kind === callerKind;
      const searchable = [
        call.caller,
        call.callee,
        call.caller_file,
        call.callee_file
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return matchesKind && (!query || searchable.includes(query));
    });
  }, [calls, callerKind, search]);

  const selectedInfo = useMemo(() => {
    if (!selected) return null;
    const callers = [...new Set(calls.filter((c) => c.callee === selected).map((c) => c.caller))];
    const callees = [...new Set(calls.filter((c) => c.caller === selected).map((c) => c.callee))];
    const sym = symbols.find((x) => x.qualified_name === selected);
    return { callers, callees, sym };
  }, [calls, selected, symbols]);

  const selectNode = (id) => {
    setSelected(id);
    const next = new URLSearchParams(searchParams);
    if (id) next.set("focus", id);
    else next.delete("focus");
    setSearchParams(next, { replace: true });
  };

  const hasFilters = Boolean(search.trim()) || callerKind !== "all";

  const callColumns = useMemo(
    () => [
      {
        key: "caller",
        label: "Appelant",
        render: (row) => (
          <div className={styles.symbolCell}>
            <strong>{row.caller ?? "—"}</strong>
            {row.caller_kind && <span>{row.caller_kind}</span>}
          </div>
        )
      },
      {
        key: "line",
        label: "Ligne",
        width: "90px",
        render: (row) => (row.line != null ? `L${row.line}` : "—")
      },
      {
        key: "callee",
        label: "Appelé",
        render: (row) => (
          <div className={styles.symbolCell}>
            <strong>{row.callee ?? "—"}</strong>
            {row.callee_kind && <span>{row.callee_kind}</span>}
          </div>
        )
      },
      {
        key: "caller_file",
        label: "Fichier",
        render: (row) => row.caller_file ?? row.callee_file ?? "—"
      }
    ],
    []
  );

  const symbolColumns = useMemo(
    () => [
      {
        key: "rank",
        label: "#",
        width: "60px",
        render: (_row, index) => String(index + 1).padStart(2, "0")
      },
      {
        key: "qualified_name",
        label: "Symbole",
        render: (row) => (
          <div className={styles.symbolCell}>
            <strong>{row.qualified_name ?? row.name ?? "—"}</strong>
            <span>
              {(row.kind ?? "symbole")} · {row.file ?? "fichier inconnu"}
            </span>
          </div>
        )
      },
      {
        key: "degree",
        label: "Degré",
        width: "100px",
        align: "right",
        render: (row) => formatNumber(row.degree)
      }
    ],
    []
  );

  return (
    <div className={styles.page}>
      <Topbar
        title="Graphe de connaissances"
        subtitle="Explorez la structure, les appels et les points centraux du dépôt analysé."
        breadcrumbs={<span>DevKnowledgeHub / Graphe</span>}
        onRefresh={async () => {
          await Promise.all([refreshHealth(), load()]);
        }}
        refreshing={loading}
      />

      <div className={styles.content}>
        <section className={styles.metrics}>
          <Card>
            <CardStat
              label="Fichiers analysés"
              value={formatNumber(stats?.files)}
              hint="dans le graphe Neo4j"
            />
          </Card>
          <Card>
            <CardStat
              label="Symboles"
              value={formatNumber(stats?.symbols)}
              hint="fonctions, classes, méthodes"
            />
          </Card>
          <Card>
            <CardStat
              label="Imports"
              value={formatNumber(stats?.imports)}
              hint="relations entre modules"
            />
          </Card>
          <Card>
            <CardStat
              label="Appels"
              value={formatNumber(stats?.calls)}
              hint="relations CALLS résolues"
            />
          </Card>
        </section>

        <Card
          title="Graphe visuel"
          subtitle="Cliquez sur un nœud pour voir ses relations. Glissez pour déplacer, zoomez avec + / −."
        >
          {calls.length === 0 ? (
            <EmptyState
              title={loading ? "Chargement du graphe..." : "Aucun graphe pour ce dépôt"}
              description={
                loading
                  ? "Récupération des relations depuis Neo4j."
                  : "Importez un dépôt dans l'onglet Dépôts pour construire son graphe."
              }
            />
          ) : (
            <div className={styles.graphLayout}>
              <ForceGraph calls={calls} selected={selected} onSelect={selectNode} />
              <aside className={styles.detail}>
                {selected && selectedInfo ? (
                  <>
                    <h3>{selected}</h3>
                    {selectedInfo.sym && (
                      <p className={styles.footnote}>
                        {selectedInfo.sym.kind} · {selectedInfo.sym.file}:{selectedInfo.sym.start_line}-
                        {selectedInfo.sym.end_line}
                      </p>
                    )}
                    <h4>Appelé par ({selectedInfo.callers.length})</h4>
                    <ul>
                      {selectedInfo.callers.map((n) => (
                        <li key={n}><button type="button" onClick={() => selectNode(n)}>{n}</button></li>
                      ))}
                      {selectedInfo.callers.length === 0 && <li className={styles.footnote}>aucun</li>}
                    </ul>
                    <h4>Appelle ({selectedInfo.callees.length})</h4>
                    <ul>
                      {selectedInfo.callees.map((n) => (
                        <li key={n}><button type="button" onClick={() => selectNode(n)}>{n}</button></li>
                      ))}
                      {selectedInfo.callees.length === 0 && <li className={styles.footnote}>aucun</li>}
                    </ul>
                    <Link to="/copilot" className={styles.askLink}>Poser une question à l'agent →</Link>
                  </>
                ) : (
                  <p className={styles.footnote}>
                    Sélectionnez un nœud pour afficher ses appelants et ses appelés.
                  </p>
                )}
              </aside>
            </div>
          )}
        </Card>

        <section className={styles.grid}>
          <Card
            title="Appels de symboles"
            subtitle={
              loading
                ? "Chargement des relations..."
                : error
                  ? error.message
                  : hasFilters
                    ? `${formatNumber(filteredCalls.length)} ${pluralize(
                        filteredCalls.length,
                        "relation"
                      )} trouvée${filteredCalls.length > 1 ? "s" : ""}`
                    : `${formatNumber(calls.length)} ${pluralize(calls.length, "relation")} chargée${calls.length > 1 ? "s" : ""}`
            }
            headerAction={
              updatedAt && (
                <span className={styles.updated}>
                  Mis à jour à {formatTime(updatedAt)}
                </span>
              )
            }
          >
            <div className={styles.filters}>
              <SearchInput
                placeholder="Rechercher un symbole, un fichier..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
              <Select
                aria-label="Filtrer par type d'appelant"
                value={callerKind}
                onChange={(event) => setCallerKind(event.target.value)}
              >
                <option value="all">Tous les types</option>
                {kinds.map((kind) => (
                  <option key={kind} value={kind}>
                    {kind}
                  </option>
                ))}
              </Select>
            </div>

            <DataTable
              columns={callColumns}
              data={filteredCalls}
              getRowKey={(row, index) =>
                `${row.caller}-${row.callee}-${row.line ?? ""}-${index}`
              }
              emptyState={
                <EmptyState
                  title="Aucune relation à afficher"
                  description={
                    error
                      ? "Vérifiez que le backend FastAPI et Neo4j sont disponibles."
                      : calls.length === 0
                        ? "Aucun appel résolu. Réindexez le dépôt pour alimenter le graphe."
                        : "Aucun résultat ne correspond aux filtres actuels."
                  }
                />
              }
            />
            <p className={styles.footnote}>
              Limité aux 200 premiers appels pour optimiser l'affichage.
            </p>
          </Card>

          <Card
            title="Symboles principaux"
            subtitle="Les nœuds les plus connectés du dépôt"
          >
            <DataTable
              columns={symbolColumns}
              data={symbols.slice(0, 10)}
              getRowKey={(row) => row.qualified_name ?? row.name ?? row.file}
              emptyState={
                <EmptyState
                  title="Aucun symbole"
                  description="Les données de symboles apparaîtront après construction du graphe."
                />
              }
            />
          </Card>
        </section>
      </div>
    </div>
  );
}
