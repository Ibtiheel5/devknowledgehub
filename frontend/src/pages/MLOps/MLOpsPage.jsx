import { useCallback, useEffect, useState } from "react";
import { Topbar } from "../../components/layout";
import { Card, CardStat, DataTable, EmptyState, StatusPill } from "../../components/ui";
import { getAgentRuns } from "../../services/mlopsApi";
import styles from "./MLOpsPage.module.css";

function formatDuration(milliseconds) {
  if (milliseconds == null) return "—";
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
}

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("fr-FR", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

export function MLOpsPage() {
  const [summary, setSummary] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getAgentRuns();
      setSummary(result.summary);
      setRuns(result.runs);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const columns = [
    {
      key: "created_at",
      label: "Date",
      render: (run) => formatDate(run.created_at)
    },
    {
      key: "repo_name",
      label: "Dépôt",
      render: (run) => <strong>{run.repo_name}</strong>
    },
    { key: "model", label: "Modèle" },
    {
      key: "status",
      label: "État",
      render: (run) => (
        <StatusPill
          status={run.status === "success" ? "ok" : "error"}
          label={run.status === "success" ? "Réussi" : "Échec"}
        />
      )
    },
    {
      key: "duration_ms",
      label: "Durée",
      align: "right",
      render: (run) => formatDuration(run.duration_ms)
    },
    { key: "retrieved_chunks", label: "Extraits RAG", align: "right" },
    { key: "graph_evidence", label: "Sources graphe", align: "right" },
    { key: "citations", label: "Citations", align: "right" }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="MLOps"
        subtitle="Suivi des exécutions de l’agent : latence, modèle et sources utilisées."
        breadcrumbs={<span>DevKnowledgeHub / MLOps</span>}
        onRefresh={load}
        refreshing={loading}
      />
      <div className={styles.content}>
        {error && (
          <Card>
            <p className={styles.error}>
              Impossible de charger les métriques MLOps : {error.message}
            </p>
          </Card>
        )}

        <section className={styles.stats}>
          <CardStat label="Exécutions" value={summary?.total ?? "—"} />
          <CardStat label="Réussies" value={summary?.successful ?? "—"} />
          <CardStat label="Échecs" value={summary?.failed ?? "—"} />
          <CardStat
            label="Durée moyenne"
            value={summary ? formatDuration(summary.avg_duration_ms) : "—"}
          />
        </section>

        <Card
          title="Dernières exécutions de l’agent"
          subtitle={
            summary?.latest_model
              ? `Modèle utilisé le plus récemment : ${summary.latest_model}`
              : "Les exécutions apparaîtront après les premières questions posées dans Copilot."
          }
        >
          <p className={styles.privacy}>
            Pour préserver la confidentialité, le texte des questions et des réponses n’est pas
            enregistré dans ces métriques.
          </p>
          <DataTable
            columns={columns}
            data={runs}
            rowKey="id"
            emptyState={
              <EmptyState
                title={loading ? "Chargement…" : "Aucune exécution enregistrée"}
                description={
                  loading
                    ? "Récupération des métriques."
                    : "Pose une question dans Copilot ; ses métriques apparaîtront ici."
                }
              />
            }
          />
        </Card>
      </div>
    </div>
  );
}
