import { useCallback, useEffect, useMemo, useState } from "react";
import { Topbar } from "../../components/layout";
import {
  Card,
  CardStat,
  DataTable,
  EmptyState,
  Select
} from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getProjectFindings } from "../../services/projectApi";
import styles from "../page.module.css";

const MODEL_OPTIONS = [
  { value: "all", label: "Tous les détecteurs" },
  { value: "vulnerability_detector", label: "Vulnérabilités" },
  { value: "code_smell_detector", label: "Code smells" },
  { value: "clone_detector", label: "Clones" }
];

function severityClass(severity) {
  if (severity === "high") return styles.badgeDanger;
  if (severity === "medium") return styles.badgeWarning;
  return styles.badgeInfo;
}

function severityLabel(finding) {
  if (finding.model_name === "clone_detector") return "clone";
  return finding.payload?.severity ?? "info";
}

export function IncidentsPage() {
  const { activeRepo } = useRepo();
  const [findings, setFindings] = useState([]);
  const [model, setModel] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getProjectFindings(activeRepo, null, 500);
      setFindings(Array.isArray(result.findings) ? result.findings : []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    if (model === "all") return findings;
    return findings.filter((finding) => finding.model_name === model);
  }, [findings, model]);

  const summary = useMemo(() => {
    const high = findings.filter((finding) => finding.payload?.severity === "high").length;
    const files = new Set(findings.map((finding) => finding.file).filter(Boolean));
    const vulnerabilities = findings.filter(
      (finding) => finding.model_name === "vulnerability_detector"
    ).length;
    return { total: findings.length, high, vulnerabilities, files: files.size };
  }, [findings]);

  const columns = [
    {
      key: "label",
      label: "Problème",
      render: (finding) => (
        <div>
          <strong>{finding.label ?? "finding"}</strong>
          <p className={styles.muted}>
            {finding.payload?.message ?? finding.payload?.detail ?? finding.model_name}
          </p>
        </div>
      )
    },
    {
      key: "severity",
      label: "Sévérité",
      render: (finding) => (
        <span className={`${styles.badge} ${severityClass(finding.payload?.severity)}`}>
          {severityLabel(finding)}
        </span>
      )
    },
    {
      key: "location",
      label: "Emplacement",
      render: (finding) => (
        <div>
          <strong>{finding.symbol || finding.file || "—"}</strong>
          {finding.payload?.line && (
            <p className={styles.muted}>Ligne {finding.payload.line}</p>
          )}
          {finding.payload?.other_file && (
            <p className={styles.muted}>avec {finding.payload.other_file}</p>
          )}
        </div>
      )
    },
    {
      key: "score",
      label: "Score",
      align: "right",
      render: (finding) =>
        finding.score == null ? "—" : `${Math.round(finding.score * 100)} %`
    }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="Incidents"
        subtitle="Vulnérabilités, code smells et duplications détectés à l'ingestion."
        breadcrumbs={<span>DevKnowledgeHub / Incidents</span>}
        onRefresh={load}
        refreshing={loading}
      />
      <div className={styles.content}>
        {error && <Card><p className={styles.error}>Impossible de charger les findings : {error.message}</p></Card>}

        <section className={styles.stats}>
          <CardStat label="Findings" value={summary.total} />
          <CardStat label="Sévérité haute" value={summary.high} />
          <CardStat label="Vulnérabilités" value={summary.vulnerabilities} />
          <CardStat label="Fichiers concernés" value={summary.files} />
        </section>

        <Card
          title="Détections"
          subtitle="Analyse statique : signaux à confirmer, pas une preuve de faille."
          headerAction={
            <Select
              aria-label="Filtrer par détecteur"
              value={model}
              onChange={(event) => setModel(event.target.value)}
            >
              {MODEL_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </Select>
          }
        >
          <DataTable
            columns={columns}
            data={filtered}
            rowKey="id"
            emptyState={
              <EmptyState
                title={loading ? "Chargement…" : "Aucun incident détecté"}
                description={
                  loading
                    ? "Analyse des findings en cours."
                    : "Relancez l'ingestion du dépôt pour exécuter les détecteurs."
                }
              />
            }
          />
        </Card>
      </div>
    </div>
  );
}
