import { useCallback, useEffect, useState } from "react";
import { Topbar } from "../../components/layout";
import { Card, CardStat, DataTable, EmptyState, StatusPill } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import {
  getAgentRuns,
  getModels,
  getMonitoring,
  getQuality
} from "../../services/mlopsApi";
import { formatDateTime } from "../../utils/format";
import styles from "./MLOpsPage.module.css";

function formatDuration(milliseconds) {
  if (milliseconds == null) return "—";
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
}

function percent(value) {
  if (value == null) return "—";
  return `${Math.round(value * 100)} %`;
}

export function MLOpsPage() {
  const { activeRepo } = useRepo();
  const [summary, setSummary] = useState(null);
  const [runs, setRuns] = useState([]);
  const [monitoring, setMonitoring] = useState(null);
  const [models, setModels] = useState([]);
  const [quality, setQuality] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [runsResult, monitoringResult, modelsResult, qualityResult] =
      await Promise.allSettled([
        getAgentRuns(),
        getMonitoring(activeRepo),
        getModels(activeRepo),
        getQuality(activeRepo)
      ]);

    if (runsResult.status === "fulfilled") {
      setSummary(runsResult.value.summary);
      setRuns(runsResult.value.runs);
    }
    if (monitoringResult.status === "fulfilled") setMonitoring(monitoringResult.value);
    if (modelsResult.status === "fulfilled") {
      setModels(Array.isArray(modelsResult.value.models) ? modelsResult.value.models : []);
    }
    if (qualityResult.status === "fulfilled") setQuality(qualityResult.value);

    const rejected = [runsResult, monitoringResult, modelsResult, qualityResult].find(
      (result) => result.status === "rejected"
    );
    if (rejected) setError(rejected.reason);
    setLoading(false);
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const agentColumns = [
    { key: "created_at", label: "Date", render: (run) => formatDateTime(new Date(run.created_at)) },
    { key: "repo_name", label: "Dépôt", render: (run) => <strong>{run.repo_name}</strong> },
    {
      key: "agent",
      label: "Agent",
      render: (run) => <span className={styles.agentBadge}>{run.agent ?? "copilot"}</span>
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
    { key: "duration_ms", label: "Durée", align: "right", render: (run) => formatDuration(run.duration_ms) },
    { key: "retrieved_chunks", label: "Extraits RAG", align: "right" },
    { key: "citations", label: "Citations", align: "right" }
  ];

  const modelColumns = [
    { key: "model_name", label: "Modèle", render: (row) => <strong>{row.model_name}</strong> },
    { key: "model_version", label: "Version", render: (row) => row.model_version ?? "—" },
    { key: "predictions", label: "Prédictions", align: "right" },
    { key: "repositories", label: "Dépôts", align: "right" },
    { key: "avg_score", label: "Score moyen", align: "right", render: (row) => percent(row.avg_score) },
    {
      key: "last_seen",
      label: "Dernière exécution",
      align: "right",
      render: (row) => (row.last_seen ? formatDateTime(new Date(row.last_seen)) : "—")
    }
  ];

  const qualityColumns = [
    { key: "model_name", label: "Détecteur" },
    { key: "label", label: "Catégorie", render: (row) => <strong>{row.label}</strong> },
    { key: "findings", label: "Findings", align: "right" },
    { key: "avg_score", label: "Score moyen", align: "right", render: (row) => percent(row.avg_score) }
  ];

  const agentSummaryColumns = [
    {
      key: "agent",
      label: "Agent",
      render: (row) => <span className={styles.agentBadge}>{row.agent}</span>
    },
    { key: "total", label: "Exécutions", align: "right" },
    { key: "successful", label: "Réussies", align: "right" },
    {
      key: "avg_duration_ms",
      label: "Durée moyenne",
      align: "right",
      render: (row) => formatDuration(row.avg_duration_ms)
    }
  ];

  const feedback = monitoring?.feedback ?? quality?.feedback;

  return (
    <div className={styles.page}>
      <Topbar
        title="MLOps"
        subtitle="Latence, qualité des détecteurs, feedback RAG et exécutions de l'agent."
        breadcrumbs={<span>DevKnowledgeHub / MLOps</span>}
        onRefresh={load}
        refreshing={loading}
      />
      <div className={styles.content}>
        {error && (
          <Card>
            <p className={styles.error}>
              Certaines métriques sont indisponibles : {error.message}
            </p>
          </Card>
        )}

        <section className={styles.stats}>
          <CardStat label="Exécutions agent" value={summary?.total ?? "—"} />
          <CardStat
            label="Taux de succès"
            value={monitoring ? percent(monitoring.agents?.success_rate) : "—"}
          />
          <CardStat label="Requêtes RAG" value={monitoring?.rag?.total ?? "—"} />
          <CardStat label="Note feedback" value={feedback?.avg_rating ?? "—"} />
        </section>

        <section className={styles.stats}>
          <CardStat
            label="Latence agent moy."
            value={summary ? formatDuration(summary.avg_duration_ms) : "—"}
          />
          <CardStat
            label="Latence RAG p95"
            value={monitoring ? formatDuration(monitoring.rag?.p95_latency_ms) : "—"}
          />
          <CardStat label="Findings" value={monitoring?.predictions?.total ?? "—"} />
          <CardStat
            label="Feedback positif"
            value={quality ? percent(quality.feedback?.positive_rate) : "—"}
          />
        </section>

        <Card
          title="Couverture des agents"
          subtitle="Exécutions enregistrées par agent spécialisé, tous dépôts confondus."
        >
          <DataTable
            columns={agentSummaryColumns}
            data={summary?.by_agent ?? []}
            rowKey="agent"
            emptyState={
              <EmptyState
                title={loading ? "Chargement..." : "Aucun agent exécuté"}
                description="Lance un agent depuis la page Agents pour alimenter cette couverture."
              />
            }
          />
        </Card>

        <Card
          title="Modèles et détecteurs"
          subtitle="Modèles ayant produit des prédictions sur le dépôt actif."
        >
          <DataTable
            columns={modelColumns}
            data={models}
            getRowKey={(row) => `${row.model_name}-${row.model_version ?? ""}`}
            emptyState={
              <EmptyState
                title={loading ? "Chargement…" : "Aucune prédiction"}
                description={
                  loading
                    ? "Récupération des modèles."
                    : "Lancez une ingestion pour exécuter les détecteurs statiques."
                }
              />
            }
          />
        </Card>

        <div className={styles.twoColumns}>
          <Card title="Qualité par catégorie" subtitle="Distribution des findings">
            <DataTable
              columns={qualityColumns}
              data={quality?.findings_by_label ?? []}
              getRowKey={(row) => `${row.model_name}-${row.label}`}
              emptyState={<EmptyState title="Aucun finding" />}
            />
          </Card>

          <Card
            title="Dernières exécutions de l'agent"
            subtitle={
              summary?.latest_model
                ? `Dernier modèle : ${summary.latest_model}`
                : "Les exécutions apparaîtront après les questions posées dans Copilot."
            }
          >
            <p className={styles.privacy}>
              Le texte des questions et des réponses n'est pas enregistré dans ces métriques.
            </p>
            <DataTable
              columns={agentColumns}
              data={runs}
              rowKey="id"
              emptyState={
                <EmptyState
                  title={loading ? "Chargement…" : "Aucune exécution enregistrée"}
                  description="Posez une question dans Copilot pour alimenter ces métriques."
                />
              }
            />
          </Card>
        </div>
      </div>
    </div>
  );
}
