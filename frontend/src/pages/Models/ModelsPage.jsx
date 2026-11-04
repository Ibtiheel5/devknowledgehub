import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, BrainCircuit, Gauge, Layers3, Target } from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Topbar } from "../../components/layout";
import { Card, CardStat, DataTable, EmptyState } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getModels, getMonitoring, getQuality } from "../../services/mlopsApi";
import { formatDateTime, formatNumber } from "../../utils/format";
import styles from "./ModelsPage.module.css";

function percent(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${Math.round(Number(value) * 100)} %`;
}

export function ModelsPage() {
  const { activeRepo } = useRepo();
  const [models, setModels] = useState([]);
  const [quality, setQuality] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [modelsResult, qualityResult, monitoringResult] = await Promise.allSettled([
      getModels(activeRepo),
      getQuality(activeRepo),
      getMonitoring(activeRepo, 7)
    ]);
    if (modelsResult.status === "fulfilled") {
      setModels(Array.isArray(modelsResult.value.models) ? modelsResult.value.models : []);
    }
    if (qualityResult.status === "fulfilled") setQuality(qualityResult.value);
    if (monitoringResult.status === "fulfilled") setMonitoring(monitoringResult.value);
    const rejected = [modelsResult, qualityResult, monitoringResult].find(
      (result) => result.status === "rejected"
    );
    if (rejected) setError(rejected.reason);
    setLoading(false);
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const totals = useMemo(() => {
    const predictions = models.reduce((sum, model) => sum + Number(model.predictions || 0), 0);
    const scores = models.map((model) => Number(model.avg_score)).filter((value) => !Number.isNaN(value));
    return {
      predictions,
      average: scores.length ? scores.reduce((sum, value) => sum + value, 0) / scores.length : null,
      labels: quality?.findings_by_label?.length ?? 0
    };
  }, [models, quality]);

  const chartData = useMemo(
    () =>
      (monitoring?.predictions_by_model ?? []).map((model) => ({
        name: model.model_name?.replace(/_/g, " "),
        findings: model.findings,
        score: Math.round(Number(model.avg_score || 0) * 100)
      })),
    [monitoring]
  );

  const qualityColumns = [
    { key: "model_name", label: "Détecteur" },
    {
      key: "label",
      label: "Catégorie",
      render: (row) => <strong>{row.label}</strong>
    },
    {
      key: "findings",
      label: "Findings",
      align: "right",
      render: (row) => formatNumber(row.findings)
    },
    {
      key: "avg_score",
      label: "Score moyen",
      align: "right",
      render: (row) => percent(row.avg_score)
    }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="Modèles ML"
        subtitle="Détecteurs statiques, qualité des prédictions et couverture par dépôt."
        breadcrumbs={<span>DevKnowledgeHub / Modèles ML</span>}
        actions={
          <span className={styles.repoChip}>Dépôt : {activeRepo}</span>
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
            label="Modèles actifs"
            value={formatNumber(models.length)}
            icon={<BrainCircuit size={18} />}
            hint={`${totals.labels} catégories de findings`}
          />
          <CardStat
            label="Prédictions"
            value={formatNumber(totals.predictions)}
            icon={<Layers3 size={18} />}
            hint={`${formatNumber(monitoring?.predictions?.files_with_findings)} fichiers concernés`}
          />
          <CardStat
            label="Score moyen"
            value={percent(totals.average)}
            icon={<Target size={18} />}
            hint="confiance moyenne des détecteurs"
          />
          <CardStat
            label="Feedback positif"
            value={percent(quality?.feedback?.positive_rate)}
            icon={<Gauge size={18} />}
            hint={`${formatNumber(quality?.feedback?.total)} retours`}
          />
        </section>

        <section className={styles.modelGrid}>
          {models.length === 0 ? (
            <Card>
              <EmptyState
                title={loading ? "Chargement..." : "Aucun modèle"}
                description="Les modèles apparaîtront après une ingestion et des prédictions."
              />
            </Card>
          ) : (
            models.map((model) => {
              const score = Math.round(Number(model.avg_score || 0) * 100);
              return (
                <article key={`${model.model_name}-${model.model_version}`} className={styles.modelCard}>
                  <div className={styles.modelHead}>
                    <span className={styles.modelIcon}>
                      <BrainCircuit size={18} />
                    </span>
                    <div>
                      <h3>{model.model_name}</h3>
                      <p>Version {model.model_version ?? "n/a"}</p>
                    </div>
                    <span className={styles.scoreBadge}>{score}%</span>
                  </div>
                  <div className={styles.scoreBar} aria-label={`Score ${score}%`}>
                    <span style={{ width: `${score}%` }} />
                  </div>
                  <dl className={styles.facts}>
                    <div>
                      <dt>Prédictions</dt>
                      <dd>{formatNumber(model.predictions)}</dd>
                    </div>
                    <div>
                      <dt>Dépôts</dt>
                      <dd>{formatNumber(model.repositories)}</dd>
                    </div>
                    <div>
                      <dt>Fichiers</dt>
                      <dd>{formatNumber(model.files)}</dd>
                    </div>
                    <div>
                      <dt>Dernière</dt>
                      <dd>{model.last_seen ? formatDateTime(new Date(model.last_seen)) : "—"}</dd>
                    </div>
                  </dl>
                </article>
              );
            })
          )}
        </section>

        <section className={styles.gridTwo}>
          <Card
            title="Prédictions par détecteur"
            subtitle="Volume de findings sur les 7 derniers jours"
            headerAction={
              <Link className={styles.link} to="/monitoring">
                Monitoring <ArrowRight size={14} />
              </Link>
            }
          >
            {chartData.length === 0 ? (
              <EmptyState
                title={loading ? "Chargement..." : "Aucune prédiction"}
                description="Aucune donnée de prédiction sur la période."
              />
            ) : (
              <div className={styles.chart}>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                    <XAxis type="number" allowDecimals={false} tickLine={false} axisLine={false} fontSize={11} />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={128}
                      tickLine={false}
                      axisLine={false}
                      fontSize={11}
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

          <Card title="Qualité par catégorie" subtitle="Findings produits par type de détecteur">
            <DataTable
              columns={qualityColumns}
              data={quality?.findings_by_label ?? []}
              getRowKey={(row) => `${row.model_name}-${row.label}`}
              emptyState={
                <EmptyState
                  title={loading ? "Chargement..." : "Aucun finding"}
                  description="Les catégories apparaîtront après ingestion du dépôt."
                />
              }
            />
          </Card>
        </section>
      </div>
    </div>
  );
}
