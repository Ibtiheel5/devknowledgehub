import { useCallback, useEffect, useMemo, useState } from "react";
import {
  BrainCircuit,
  Download,
  FileBarChart,
  FileJson,
  FileSpreadsheet,
  ShieldAlert,
  Sparkles
} from "lucide-react";
import { Topbar } from "../../components/layout";
import { Button, Card, CardStat, DataTable, EmptyState } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getProject, getProjectFindings } from "../../services/projectApi";
import { getAgentRuns, getModels, getMonitoring, getQuality } from "../../services/mlopsApi";
import { formatDateTime, formatNumber } from "../../utils/format";
import { downloadCsv, downloadJson } from "../../utils/export";
import styles from "./ReportsPage.module.css";

function percent(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  return `${Math.round(Number(value) * 100)} %`;
}

function severityOf(finding) {
  const raw = String(finding?.payload?.severity || finding?.label || "").toLowerCase();
  if (raw.includes("critical")) return "critique";
  if (raw.includes("high") || raw.includes("vuln")) return "élevé";
  if (raw.includes("medium") || raw.includes("smell") || raw.includes("duplicate")) return "moyen";
  if (raw.includes("low")) return "faible";
  return "info";
}

export function ReportsPage() {
  const { activeRepo } = useRepo();
  const [project, setProject] = useState(null);
  const [findings, setFindings] = useState([]);
  const [models, setModels] = useState([]);
  const [quality, setQuality] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.allSettled([
      getProject(activeRepo),
      getProjectFindings(activeRepo, null, 500),
      getModels(activeRepo),
      getQuality(activeRepo),
      getMonitoring(activeRepo, 30),
      getAgentRuns(200)
    ]);
    const [projectResult, findingsResult, modelsResult, qualityResult, monitoringResult, runsResult] = results;
    if (projectResult.status === "fulfilled") setProject(projectResult.value);
    if (findingsResult.status === "fulfilled") {
      setFindings(Array.isArray(findingsResult.value.findings) ? findingsResult.value.findings : []);
    }
    if (modelsResult.status === "fulfilled") {
      setModels(Array.isArray(modelsResult.value.models) ? modelsResult.value.models : []);
    }
    if (qualityResult.status === "fulfilled") setQuality(qualityResult.value);
    if (monitoringResult.status === "fulfilled") setMonitoring(monitoringResult.value);
    if (runsResult.status === "fulfilled") {
      setRuns(Array.isArray(runsResult.value.runs) ? runsResult.value.runs : []);
    }
    const rejected = results.find((result) => result.status === "rejected");
    if (rejected) setError(rejected.reason);
    setLoading(false);
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const repoRuns = useMemo(
    () => runs.filter((run) => run.repo_name === activeRepo),
    [runs, activeRepo]
  );

  const reportDate = useMemo(() => new Date(), [loading]);

  const summary = useMemo(() => {
    const severity = { critique: 0, élevé: 0, moyen: 0, faible: 0, info: 0 };
    for (const finding of findings) severity[severityOf(finding)] += 1;
    return { severity };
  }, [findings]);

  const findingColumns = [
    {
      key: "label",
      label: "Finding",
      render: (finding) => (
        <div>
          <strong>{finding.label ?? finding.model_name ?? "Finding"}</strong>
          <p className={styles.muted}>{finding.file ?? finding.target_id ?? "cible inconnue"}</p>
        </div>
      )
    },
    {
      key: "severity",
      label: "Sévérité",
      render: (finding) => <span className={styles.badge}>{severityOf(finding)}</span>
    },
    { key: "model_name", label: "Détecteur", render: (finding) => finding.model_name ?? "—" },
    {
      key: "score",
      label: "Score",
      align: "right",
      render: (finding) => percent(finding.score)
    }
  ];

  const exportFindings = () =>
    downloadCsv(
      `${activeRepo}-findings.csv`,
      findings,
      [
        { key: "label", label: "label" },
        { key: "model_name", label: "detecteur" },
        { key: "file", label: "fichier" },
        { key: "target_id", label: "cible" },
        { key: "score", label: "score" },
        { key: "severity", label: "severite", value: severityOf },
        { key: "created_at", label: "date" }
      ]
    );

  const exportModels = () =>
    downloadCsv(`${activeRepo}-modeles.csv`, models, [
      { key: "model_name", label: "modele" },
      { key: "model_version", label: "version" },
      { key: "predictions", label: "predictions" },
      { key: "repositories", label: "depots" },
      { key: "files", label: "fichiers" },
      { key: "avg_score", label: "score_moyen" },
      { key: "last_seen", label: "derniere_execution" }
    ]);

  const exportMonitoring = () =>
    downloadCsv(`${activeRepo}-monitoring.csv`, repoRuns, [
      { key: "created_at", label: "date" },
      { key: "agent", label: "agent" },
      { key: "model", label: "modele" },
      { key: "status", label: "statut" },
      { key: "duration_ms", label: "duree_ms" },
      { key: "retrieved_chunks", label: "extraits" },
      { key: "citations", label: "citations" }
    ]);

  const exportFullReport = () =>
    downloadJson(`${activeRepo}-rapport.json`, {
      generated_at: new Date().toISOString(),
      repo_name: activeRepo,
      project,
      findings,
      models,
      quality,
      monitoring,
      agent_runs: repoRuns
    });

  const cards = [
    {
      title: "Rapport de synthèse",
      description: "Projet, indicateurs, architecture, findings et métriques agrégées.",
      icon: <FileBarChart size={18} />,
      meta: "JSON complet",
      action: exportFullReport,
      label: "Exporter le rapport"
    },
    {
      title: "Findings du code",
      description: `${formatNumber(findings.length)} finding(s), sévérité et scores des détecteurs.`,
      icon: <ShieldAlert size={18} />,
      meta: "CSV",
      action: exportFindings,
      label: "Exporter les findings"
    },
    {
      title: "Modèles et qualité",
      description: `${formatNumber(models.length)} modèle(s), prédictions et couverture.`,
      icon: <BrainCircuit size={18} />,
      meta: "CSV",
      action: exportModels,
      label: "Exporter les modèles"
    },
    {
      title: "Exécutions monitoring",
      description: `${formatNumber(repoRuns.length)} exécution(s) d'agents sur ce dépôt.`,
      icon: <Sparkles size={18} />,
      meta: "CSV",
      action: exportMonitoring,
      label: "Exporter le monitoring"
    }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="Rapports"
        subtitle="Exportez les analyses, findings et métriques de la plateforme."
        breadcrumbs={<span>DevKnowledgeHub / Rapports</span>}
        actions={
          <Button variant="primary" onClick={exportFullReport} disabled={loading}>
            <Download size={15} /> Exporter tout
          </Button>
        }
        onRefresh={load}
        refreshing={loading}
      />

      <div className={styles.content}>
        {error && (
          <Card>
            <p className={styles.error}>Certaines données sont indisponibles : {error.message}</p>
          </Card>
        )}

        <section className={styles.hero}>
          <div>
            <span className={styles.kicker}>Rapport du dépôt</span>
            <h2>{project?.name ?? activeRepo}</h2>
            <p>
              Généré le {formatDateTime(reportDate)} · commit{" "}
              <code>{project?.commit_sha?.slice(0, 10) ?? "n/a"}</code> ·{" "}
              {project?.status ?? "statut inconnu"}
            </p>
          </div>
          <div className={styles.heroStats}>
            <span>
              <strong>{formatNumber(findings.length)}</strong> findings
            </span>
            <span>
              <strong>{percent(monitoring?.agents?.success_rate)}</strong> succès agents
            </span>
            <span>
              <strong>{formatNumber(models.length)}</strong> modèles
            </span>
          </div>
        </section>

        <section className={styles.stats}>
          <CardStat label="Findings" value={formatNumber(findings.length)} />
          <CardStat label="Critiques" value={formatNumber(summary.severity.critique)} />
          <CardStat label="Élevés" value={formatNumber(summary.severity.élevé)} />
          <CardStat label="Catégories" value={formatNumber(quality?.findings_by_label?.length)} />
        </section>

        <section className={styles.reportGrid}>
          {cards.map((card) => (
            <article key={card.title} className={styles.reportCard}>
              <span className={styles.reportIcon}>{card.icon}</span>
              <h3>{card.title}</h3>
              <p>{card.description}</p>
              <div className={styles.reportFooter}>
                <span className={styles.meta}>
                  {card.meta.startsWith("JSON") ? <FileJson size={13} /> : <FileSpreadsheet size={13} />}
                  {card.meta}
                </span>
                <Button variant="outline" onClick={card.action} disabled={loading}>
                  <Download size={14} /> {card.label}
                </Button>
              </div>
            </article>
          ))}
        </section>

        <Card
          title="Aperçu des findings"
          subtitle={`${findings.length} résultat(s) · export CSV disponible`}
          headerAction={
            <Button variant="outline" onClick={exportFindings} disabled={loading || findings.length === 0}>
              <Download size={14} /> CSV
            </Button>
          }
        >
          <DataTable
            columns={findingColumns}
            data={findings.slice(0, 30)}
            rowKey="id"
            emptyState={
              <EmptyState
                title={loading ? "Chargement..." : "Aucun finding"}
                description="Les findings apparaîtront après l'analyse du dépôt."
              />
            }
          />
        </Card>

        <Card title="Qualité par catégorie" subtitle="Synthèse des détecteurs">
          <DataTable
            columns={[
              { key: "model_name", label: "Détecteur" },
              { key: "label", label: "Catégorie", render: (row) => <strong>{row.label}</strong> },
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
            ]}
            data={quality?.findings_by_label ?? []}
            getRowKey={(row) => `${row.model_name}-${row.label}`}
            emptyState={
              <EmptyState
                title={loading ? "Chargement..." : "Aucune catégorie"}
                description="Aucune donnée de qualité disponible."
              />
            }
          />
        </Card>
      </div>
    </div>
  );
}
