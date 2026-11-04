import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Clock3,
  DatabaseZap,
  Gauge,
  ShieldCheck,
  Sparkles
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Topbar } from "../../components/layout";
import { Card, CardStat, DataTable, EmptyState, Select, StatusPill } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getAgentRuns, getMonitoring } from "../../services/mlopsApi";
import { formatDateTime, formatNumber } from "../../utils/format";
import styles from "./MonitoringPage.module.css";

const WINDOWS = [7, 14, 30, 90];

function formatDuration(milliseconds) {
  if (milliseconds == null) return "—";
  if (milliseconds < 1000) return `${milliseconds} ms`;
  return `${(milliseconds / 1000).toFixed(1)} s`;
}

function percent(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${Math.round(Number(value) * 100)} %`;
}

export function MonitoringPage() {
  const { activeRepo } = useRepo();
  const [days, setDays] = useState(7);
  const [monitoring, setMonitoring] = useState(null);
  const [runs, setRuns] = useState([]);
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [monitoringResult, runsResult] = await Promise.allSettled([
      getMonitoring(activeRepo, days),
      getAgentRuns(100)
    ]);
    if (monitoringResult.status === "fulfilled") setMonitoring(monitoringResult.value);
    if (runsResult.status === "fulfilled") {
      setRuns(Array.isArray(runsResult.value.runs) ? runsResult.value.runs : []);
      setSummary(runsResult.value.summary ?? null);
    }
    const rejected = [monitoringResult, runsResult].find((result) => result.status === "rejected");
    if (rejected) setError(rejected.reason);
    setLoading(false);
  }, [activeRepo, days]);

  useEffect(() => {
    load();
  }, [load]);

  const agentStatusData = useMemo(
    () => [
      {
        name: "Succès",
        value: monitoring?.agents?.successful ?? 0,
        color: "var(--success)"
      },
      {
        name: "Échecs",
        value: monitoring?.agents?.failed ?? 0,
        color: "var(--danger)"
      }
    ],
    [monitoring]
  );

  const ingestionData = useMemo(
    () => [
      { name: "Réussies", value: monitoring?.ingestion?.succeeded ?? 0, color: "var(--success)" },
      { name: "Échecs", value: monitoring?.ingestion?.failed ?? 0, color: "var(--danger)" }
    ],
    [monitoring]
  );

  const modelData = useMemo(
    () =>
      (monitoring?.predictions_by_model ?? []).map((model) => ({
        name: model.model_name?.replace(/_/g, " "),
        findings: model.findings,
        score: Math.round(Number(model.avg_score || 0) * 100)
      })),
    [monitoring]
  );

  const recentRuns = useMemo(
    () => runs.filter((run) => !activeRepo || run.repo_name === activeRepo).slice(0, 20),
    [runs, activeRepo]
  );

  const runColumns = [
    {
      key: "created_at",
      label: "Date",
      render: (run) => (run.created_at ? formatDateTime(new Date(run.created_at)) : "—")
    },
    {
      key: "agent",
      label: "Agent",
      render: (run) => <span className={styles.agentBadge}>{run.agent ?? "copilot"}</span>
    },
    {
      key: "status",
      label: "Statut",
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
    {
      key: "retrieved_chunks",
      label: "Extraits",
      align: "right",
      render: (run) => formatNumber(run.retrieved_chunks)
    },
    {
      key: "citations",
      label: "Citations",
      align: "right",
      render: (run) => formatNumber(run.citations)
    }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="Monitoring"
        subtitle="Latence, réussite des agents, ingestion RAG et qualité des prédictions."
        breadcrumbs={<span>DevKnowledgeHub / Monitoring</span>}
        actions={
          <Select
            aria-label="Fenêtre d'analyse"
            value={days}
            onChange={(event) => setDays(Number(event.target.value))}
          >
            {WINDOWS.map((value) => (
              <option key={value} value={value}>
                {value} jours
              </option>
            ))}
          </Select>
        }
        onRefresh={load}
        refreshing={loading}
      />

      <div className={styles.content}>
        {error && (
          <Card>
            <p className={styles.error}>Certaines métriques sont indisponibles : {error.message}</p>
          </Card>
        )}

        <section className={styles.stats}>
          <CardStat
            label="Exécutions agents"
            value={formatNumber(monitoring?.agents?.total)}
            icon={<Activity size={18} />}
            hint={`${formatNumber(monitoring?.agents?.successful)} réussies · ${formatNumber(monitoring?.agents?.failed)} échecs`}
          />
          <CardStat
            label="Taux de succès"
            value={percent(monitoring?.agents?.success_rate)}
            icon={<ShieldCheck size={18} />}
            hint={`p95 ${formatDuration(monitoring?.agents?.p95_duration_ms)}`}
          />
          <CardStat
            label="Requêtes RAG"
            value={formatNumber(monitoring?.rag?.total)}
            icon={<DatabaseZap size={18} />}
            hint={`${formatNumber(monitoring?.rag?.citations)} citations`}
          />
          <CardStat
            label="Prédictions"
            value={formatNumber(monitoring?.predictions?.total)}
            icon={<Sparkles size={18} />}
            hint={`score moyen ${percent(monitoring?.predictions?.avg_score)}`}
          />
        </section>

        <section className={styles.statsSecondary}>
          <div className={styles.miniStat}>
            <span>
              <Clock3 size={15} /> Latence agent moyenne
            </span>
            <strong>{formatDuration(monitoring?.agents?.avg_duration_ms)}</strong>
          </div>
          <div className={styles.miniStat}>
            <span>
              <Gauge size={15} /> Latence RAG p95
            </span>
            <strong>{formatDuration(monitoring?.rag?.p95_latency_ms)}</strong>
          </div>
          <div className={styles.miniStat}>
            <span>
              <DatabaseZap size={15} /> Ingestion moyenne
            </span>
            <strong>
              {monitoring?.ingestion?.avg_duration_seconds != null
                ? `${Math.round(monitoring.ingestion.avg_duration_seconds)} s`
                : "—"}
            </strong>
          </div>
          <div className={styles.miniStat}>
            <span>
              <Sparkles size={15} /> Fichiers avec findings
            </span>
            <strong>{formatNumber(monitoring?.predictions?.files_with_findings)}</strong>
          </div>
        </section>

        <section className={styles.gridThree}>
          <Card title="Agents" subtitle={`Sur ${days} jours`}>
            <div className={styles.chart}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={agentStatusData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={2}
                  >
                    {agentStatusData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid var(--border)",
                      fontSize: 12
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className={styles.legend}>
              {agentStatusData.map((entry) => (
                <span key={entry.name}>
                  <i style={{ background: entry.color }} />
                  {entry.name} · {entry.value}
                </span>
              ))}
            </div>
          </Card>

          <Card title="Ingestion" subtitle="Analyses de dépôts">
            <div className={styles.chart}>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={ingestionData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={48}
                    outerRadius={72}
                    paddingAngle={2}
                  >
                    {ingestionData.map((entry) => (
                      <Cell key={entry.name} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      borderRadius: 10,
                      border: "1px solid var(--border)",
                      fontSize: 12
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className={styles.legend}>
              {ingestionData.map((entry) => (
                <span key={entry.name}>
                  <i style={{ background: entry.color }} />
                  {entry.name} · {entry.value}
                </span>
              ))}
            </div>
          </Card>

          <Card title="Prédictions par modèle" subtitle="Volume de findings">
            {modelData.length === 0 ? (
              <EmptyState
                title={loading ? "Chargement..." : "Aucune prédiction"}
                description="Aucune prédiction sur la période."
              />
            ) : (
              <div className={styles.chart}>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={modelData} layout="vertical" margin={{ left: 4, right: 12 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                    <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} fontSize={10} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={104}
                      tickLine={false}
                      axisLine={false}
                      fontSize={10}
                    />
                    <Tooltip
                      contentStyle={{
                        borderRadius: 10,
                        border: "1px solid var(--border)",
                        fontSize: 12
                      }}
                    />
                    <Bar dataKey="findings" fill="var(--brand)" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </Card>
        </section>

        <Card
          title="Exécutions récentes"
          subtitle={`${recentRuns.length} exécution(s) pour ${activeRepo}`}
        >
          <DataTable
            columns={runColumns}
            data={recentRuns}
            rowKey="id"
            emptyState={
              <EmptyState
                title={loading ? "Chargement..." : "Aucune exécution"}
                description="Lancez un agent ou une question Copilot pour alimenter le monitoring."
              />
            }
          />
        </Card>

        {summary && (
          <p className={styles.footnote}>
            Agrégat global : {formatNumber(summary.total)} exécutions ·{" "}
            {formatNumber(summary.successful)} réussies ·{" "}
            {formatNumber(summary.failed)} échecs · modèle {summary.latest_model ?? "n/a"}.
          </p>
        )}
      </div>
    </div>
  );
}
