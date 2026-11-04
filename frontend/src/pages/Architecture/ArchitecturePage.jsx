import { useCallback, useEffect, useState } from "react";
import { Topbar } from "../../components/layout";
import {
  Card,
  CardStat,
  DataTable,
  EmptyState,
  StatusPill
} from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getProjectArchitecture } from "../../services/projectApi";
import { formatNumber } from "../../utils/format";
import styles from "../page.module.css";

export function ArchitecturePage() {
  const { activeRepo } = useRepo();
  const [architecture, setArchitecture] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setArchitecture(await getProjectArchitecture(activeRepo));
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const languages = Object.entries(architecture?.languages ?? {});
  const technologies = architecture?.technologies ?? [];
  const files = architecture?.overview?.files ?? [];
  const modules = architecture?.overview?.modules ?? [];

  return (
    <div className={styles.page}>
      <Topbar
        title="Architecture"
        subtitle="Vue structurelle du dépôt : langages, technologies et modules centraux."
        breadcrumbs={<span>DevKnowledgeHub / Architecture</span>}
        onRefresh={load}
        refreshing={loading}
      />
      <div className={styles.content}>
        {error && <Card><p className={styles.error}>Impossible de charger l'architecture : {error.message}</p></Card>}

        <section className={styles.stats}>
          <CardStat label="Langages" value={languages.length} />
          <CardStat label="Technologies" value={technologies.length} />
          <CardStat label="Fichiers clés" value={files.length} />
          <CardStat label="Modules importés" value={modules.length} />
        </section>

        <div className={styles.grid}>
          <Card
            title="Projet"
            subtitle={architecture?.project_type ? `Type : ${architecture.project_type}` : "Type non détecté"}
          >
            <div className={styles.row}>
              <StatusPill
                status={architecture?.commit_sha ? "ok" : "idle"}
                label={architecture?.commit_sha ? `commit ${architecture.commit_sha.slice(0, 8)}` : "sans commit"}
              />
            </div>
            <h3>Langages</h3>
            <div className={styles.kv}>
              {languages.length === 0 ? (
                <p className={styles.muted}>Aucun langage détecté.</p>
              ) : (
                languages.map(([language, count]) => (
                  <div key={language} className={styles.kvItem}>
                    <span>{language}</span>
                    <strong>{formatNumber(count)}</strong>
                  </div>
                ))
              )}
            </div>
          </Card>

          <Card title="Technologies" subtitle="Frameworks, bases de données et outillage">
            {technologies.length === 0 ? (
              <p className={styles.muted}>Aucune technologie détectée.</p>
            ) : (
              <div className={styles.row}>
                {technologies.map((technology) => {
                  const name =
                    typeof technology === "string" ? technology : technology.name;
                  const category =
                    typeof technology === "string" ? null : technology.category;
                  return (
                    <span
                      key={`${category ?? "tech"}-${name}`}
                      className={styles.badge}
                      title={category ? `Catégorie : ${category}` : undefined}
                    >
                      {name}
                    </span>
                  );
                })}
              </div>
            )}
          </Card>
        </div>

        <div className={styles.grid}>
          <Card title="Fichiers clés" subtitle="Fichiers les plus riches en symboles">
            <DataTable
              columns={[
                { key: "path", label: "Fichier" },
                { key: "language", label: "Langage" },
                {
                  key: "symbols",
                  label: "Symboles",
                  align: "right",
                  render: (row) => formatNumber(row.symbols)
                }
              ]}
              data={files}
              getRowKey={(row) => row.path}
              emptyState={
                <EmptyState
                  title="Aucun fichier"
                  description="Construisez le graphe pour afficher la structure du dépôt."
                />
              }
            />
          </Card>

          <Card title="Modules les plus importés" subtitle="Dépendances internes et externes">
            <DataTable
              columns={[
                { key: "name", label: "Module" },
                {
                  key: "files",
                  label: "Fichiers",
                  align: "right",
                  render: (row) => formatNumber(row.files)
                }
              ]}
              data={modules}
              getRowKey={(row) => row.name}
              emptyState={
                <EmptyState
                  title="Aucun module"
                  description="Les imports apparaîtront après construction du graphe."
                />
              }
            />
          </Card>
        </div>
      </div>
    </div>
  );
}
