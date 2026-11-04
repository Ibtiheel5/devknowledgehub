import { useCallback, useEffect, useMemo, useState } from "react";
import { Topbar } from "../../components/layout";
import {
  Card,
  CardStat,
  DataTable,
  EmptyState,
  SearchInput
} from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getRepoStats, getRepoSymbols } from "../../services/graphApi";
import { getProjectFindings } from "../../services/projectApi";
import { formatDateTime, formatNumber } from "../../utils/format";
import styles from "../page.module.css";

function severityOf(finding) {
  const raw = String(finding?.payload?.severity || finding?.label || "").toLowerCase();
  if (raw.includes("critical")) return "critique";
  if (raw.includes("high") || raw.includes("vuln")) return "élevé";
  if (raw.includes("medium") || raw.includes("smell") || raw.includes("duplicate")) return "moyen";
  if (raw.includes("low")) return "faible";
  return "info";
}

function severityClass(severity) {
  if (severity === "critique" || severity === "élevé") return styles.badgeDanger;
  if (severity === "moyen") return styles.badgeWarning;
  return styles.badgeInfo;
}

export function CodeIntelligencePage() {
  const { activeRepo } = useRepo();
  const [stats, setStats] = useState(null);
  const [symbols, setSymbols] = useState([]);
  const [findings, setFindings] = useState([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [statsResult, symbolsResult, findingsResult] = await Promise.allSettled([
      getRepoStats(activeRepo),
      getRepoSymbols(activeRepo, 200),
      getProjectFindings(activeRepo, null, 500)
    ]);
    if (statsResult.status === "fulfilled") setStats(statsResult.value);
    if (symbolsResult.status === "fulfilled") {
      setSymbols(Array.isArray(symbolsResult.value) ? symbolsResult.value : []);
    }
    if (findingsResult.status === "fulfilled") {
      setFindings(Array.isArray(findingsResult.value.findings) ? findingsResult.value.findings : []);
    }
    const rejected = [statsResult, symbolsResult, findingsResult].find(
      (result) => result.status === "rejected"
    );
    if (rejected) setError(rejected.reason);
    setLoading(false);
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const summary = useMemo(() => {
    const classes = symbols.filter((symbol) => symbol.kind === "class").length;
    const functions = symbols.filter(
      (symbol) => symbol.kind === "function" || symbol.kind === "method"
    ).length;
    const withBases = symbols.filter((symbol) => (symbol.bases ?? []).length > 0).length;
    const critical = findings.filter((finding) => severityOf(finding) === "critique").length;
    const high = findings.filter((finding) => severityOf(finding) === "élevé").length;
    return { classes, functions, withBases, findings: findings.length, critical, high };
  }, [symbols, findings]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return symbols;
    return symbols.filter((symbol) =>
      [symbol.qualified_name, symbol.name, symbol.file, symbol.kind, ...(symbol.bases ?? [])]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [symbols, search]);

  const columns = [
    {
      key: "qualified_name",
      label: "Symbole",
      render: (symbol) => (
        <div>
          <strong>{symbol.qualified_name ?? symbol.name}</strong>
          <p className={styles.muted}>
            {symbol.kind ?? "symbole"} · {symbol.file ?? "fichier inconnu"}
            {symbol.start_line ? `:${symbol.start_line}` : ""}
          </p>
        </div>
      )
    },
    {
      key: "bases",
      label: "Héritage",
      render: (symbol) =>
        (symbol.bases ?? []).length > 0 ? symbol.bases.join(", ") : "—"
    },
    {
      key: "degree",
      label: "Degré",
      align: "right",
      render: (symbol) => formatNumber(symbol.degree)
    }
  ];

  const findingColumns = [
    {
      key: "label",
      label: "Finding",
      render: (finding) => (
        <div>
          <strong>{finding.label ?? finding.model_name ?? "Finding"}</strong>
          <p className={styles.muted}>{finding.model_name ?? "détecteur inconnu"}</p>
        </div>
      )
    },
    {
      key: "file",
      label: "Emplacement",
      render: (finding) => finding.file ?? finding.target_id ?? "—"
    },
    {
      key: "severity",
      label: "Sévérité",
      render: (finding) => {
        const severity = severityOf(finding);
        return <span className={`${styles.badge} ${severityClass(severity)}`}>{severity}</span>;
      }
    },
    {
      key: "score",
      label: "Score",
      align: "right",
      render: (finding) =>
        finding.score == null ? "—" : `${Math.round(Number(finding.score) * 100)} %`
    },
    {
      key: "created_at",
      label: "Date",
      align: "right",
      render: (finding) =>
        finding.created_at ? formatDateTime(new Date(finding.created_at)) : "—"
    }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="Analyse du code"
        subtitle="Symboles, héritage, findings et qualité du code du dépôt actif."
        breadcrumbs={<span>DevKnowledgeHub / Analyse du code</span>}
        onRefresh={load}
        refreshing={loading}
      />
      <div className={styles.content}>
        {error && <Card><p className={styles.error}>Certaines données sont indisponibles : {error.message}</p></Card>}

        <section className={styles.stats}>
          <CardStat
            label="Symboles"
            value={formatNumber(stats?.symbols ?? symbols.length)}
            hint={`${summary.withBases} avec héritage`}
          />
          <CardStat label="Classes" value={summary.classes} />
          <CardStat label="Fonctions / méthodes" value={summary.functions} />
          <CardStat
            label="Findings"
            value={summary.findings}
            hint={`${summary.critical} critiques · ${summary.high} élevés`}
          />
        </section>

        <Card
          title="Exploration des symboles"
          subtitle={`${filtered.length} symbole(s) · ${summary.withBases} avec héritage`}
          headerAction={
            <SearchInput
              placeholder="Filtrer par nom, fichier, type..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          }
        >
          <DataTable
            columns={columns}
            data={filtered}
            getRowKey={(symbol) => symbol.qualified_name ?? symbol.name}
            emptyState={
              <EmptyState
                title={loading ? "Chargement…" : "Aucun symbole"}
                description={
                  loading
                    ? "Récupération des symboles depuis Neo4j."
                    : "Construisez le graphe ou relancez l'ingestion du dépôt."
                }
              />
            }
          />
        </Card>

        <Card
          title="Findings du dépôt"
          subtitle={`${findings.length} finding(s) détecté(s) par les détecteurs`}
        >
          <DataTable
            columns={findingColumns}
            data={findings}
            rowKey="id"
            emptyState={
              <EmptyState
                title={loading ? "Chargement…" : "Aucun finding"}
                description={
                  loading
                    ? "Récupération des résultats des détecteurs."
                    : "L'ingestion ou les prédictions n'ont pas encore produit de résultats."
                }
              />
            }
          />
        </Card>
      </div>
    </div>
  );
}
