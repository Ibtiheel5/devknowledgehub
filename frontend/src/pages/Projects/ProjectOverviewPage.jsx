import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Boxes,
  FileCode2,
  GitBranch,
  Layers,
  ShieldAlert,
  Terminal,
  Ticket
} from "lucide-react";
import { Topbar } from "../../components/layout";
import { Button, Card, CardStat, EmptyState, StatusPill } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getProject, getProjectArchitecture, getProjectFindings, getProjectIssues } from "../../services/projectApi";
import { formatDateTime, formatNumber } from "../../utils/format";
import styles from "./ProjectOverviewPage.module.css";

function statusTone(status) {
  if (status === "ready" || status === "succeeded") return "ok";
  if (status === "failed" || status === "error") return "error";
  if (status === "indexing" || status === "pending" || status === "running") return "warn";
  return "idle";
}

function severityOf(finding) {
  const raw = String(finding?.payload?.severity || finding?.label || "").toLowerCase();
  if (raw.includes("critical")) return "critical";
  if (raw.includes("high") || raw.includes("vuln")) return "high";
  if (raw.includes("medium") || raw.includes("smell") || raw.includes("duplicate")) return "medium";
  if (raw.includes("low")) return "low";
  return "info";
}

export function ProjectOverviewPage() {
  const navigate = useNavigate();
  const { activeRepo } = useRepo();
  const [project, setProject] = useState(null);
  const [architecture, setArchitecture] = useState(null);
  const [findings, setFindings] = useState([]);
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const [projectResult, architectureResult, findingsResult, issuesResult] = await Promise.allSettled([
      getProject(activeRepo),
      getProjectArchitecture(activeRepo),
      getProjectFindings(activeRepo, null, 300),
      getProjectIssues(activeRepo)
    ]);
    if (projectResult.status === "fulfilled") setProject(projectResult.value);
    else setError(projectResult.reason);
    if (architectureResult.status === "fulfilled") setArchitecture(architectureResult.value);
    if (findingsResult.status === "fulfilled") {
      setFindings(Array.isArray(findingsResult.value.findings) ? findingsResult.value.findings : []);
    }
    if (issuesResult.status === "fulfilled") {
      setIssues(Array.isArray(issuesResult.value.issues) ? issuesResult.value.issues : []);
    }
    setLoading(false);
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const severity = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const finding of findings) counts[severityOf(finding)] += 1;
    return counts;
  }, [findings]);

  const languages = useMemo(() => {
    const source = project?.languages ?? architecture?.languages ?? {};
    const total = Object.values(source).reduce((sum, value) => sum + Number(value || 0), 0);
    return Object.entries(source).map(([name, count]) => ({
      name,
      count: Number(count || 0),
      percent: total ? Math.round((Number(count || 0) / total) * 100) : 0
    }));
  }, [project, architecture]);

  const technologies = project?.technologies ?? architecture?.technologies ?? [];
  const latestRun = project?.latest_run;
  const health = project?.status === "ready" ? "Bon" : project?.status === "failed" ? "À corriger" : "En cours";

  return (
    <div className={styles.page}>
      <Topbar
        title={project?.name ?? activeRepo}
        subtitle="Vue d'ensemble du dépôt, de sa santé et de ses analyses."
        breadcrumbs={
          <span>
            <Link to="/projects">Projets</Link> / {project?.name ?? activeRepo}
          </span>
        }
        actions={
          <>
            <Button variant="outline" onClick={() => navigate("/projects")}>
              Changer de projet
            </Button>
            <Button variant="primary" onClick={load} loading={loading}>
              Actualiser
            </Button>
          </>
        }
        onRefresh={load}
        refreshing={loading}
      />

      <div className={styles.content}>
        {error && (
          <Card>
            <p className={styles.error}>
              Impossible de charger le projet « {activeRepo} » : {error.message}
            </p>
          </Card>
        )}

        {!project && !error ? (
          <Card>
            <EmptyState
              title={loading ? "Chargement du projet..." : "Projet introuvable"}
              description={
                loading
                  ? "Récupération des informations du dépôt."
                  : "Sélectionnez un projet dans la page Projets."
              }
              action={
                <Button variant="primary" onClick={() => navigate("/projects")}>
                  Voir les projets
                </Button>
              }
            />
          </Card>
        ) : (
          <>
            <section className={styles.hero}>
              <div className={styles.heroMain}>
                <span className={styles.kicker}>Projet actif</span>
                <h2>{project?.name ?? activeRepo}</h2>
                <p>{project?.git_url ?? "URL du dépôt non renseignée"}</p>
                <div className={styles.heroActions}>
                  <Link className={styles.primaryLink} to="/architecture">
                    <GitBranch size={16} /> Explorer le graphe
                  </Link>
                  <Link className={styles.secondaryLink} to="/code-analysis">
                    <ShieldAlert size={16} /> Voir les findings
                  </Link>
                  <Link className={styles.secondaryLink} to="/assistant">
                    <Terminal size={16} /> Poser une question
                  </Link>
                </div>
              </div>
              <div className={styles.heroSide}>
                <StatusPill status={statusTone(project?.status)} label={project?.status ?? "inconnu"} />
                <dl className={styles.heroFacts}>
                  <div>
                    <dt>Santé</dt>
                    <dd>{health}</dd>
                  </div>
                  <div>
                    <dt>Dernière analyse</dt>
                    <dd>{latestRun?.finished_at ? formatDateTime(new Date(latestRun.finished_at)) : "—"}</dd>
                  </div>
                  <div>
                    <dt>Commit</dt>
                    <dd className={styles.mono}>{project?.commit_sha?.slice(0, 10) ?? "—"}</dd>
                  </div>
                  <div>
                    <dt>Type</dt>
                    <dd>{project?.project_type ?? "—"}</dd>
                  </div>
                </dl>
              </div>
            </section>

            <section className={styles.stats}>
              <CardStat
                label="Fichiers analysés"
                value={formatNumber(latestRun?.files ?? architecture?.overview?.files?.length)}
                icon={<FileCode2 size={18} />}
                hint={`${formatNumber(project?.rag?.chunks)} chunks RAG`}
              />
              <CardStat
                label="Symboles"
                value={formatNumber(latestRun?.symbols ?? architecture?.overview?.symbols?.length)}
                icon={<Layers size={18} />}
                hint={`${formatNumber(latestRun?.chunks)} chunks d'analyse`}
              />
              <CardStat
                label="Findings"
                value={formatNumber(findings.length)}
                icon={<ShieldAlert size={18} />}
                hint={`${severity.critical} critiques · ${severity.high} élevés`}
              />
              <CardStat
                label="Tickets"
                value={formatNumber(issues.length)}
                icon={<Ticket size={18} />}
                hint={`${issues.filter((issue) => issue.status !== "closed").length} ouverts`}
              />
            </section>

            <section className={styles.gridTwo}>
              <Card title="Langages et technologies" subtitle="Détection statique du dépôt">
                <div className={styles.languageList}>
                  {languages.length === 0 ? (
                    <EmptyState title="Aucun langage détecté" description="Relancez l'analyse du dépôt." />
                  ) : (
                    languages.map((language) => (
                      <div key={language.name} className={styles.languageRow}>
                        <div>
                          <strong>{language.name}</strong>
                          <span>{language.count} fichier(s)</span>
                        </div>
                        <div className={styles.bar}>
                          <span style={{ width: `${language.percent}%` }} />
                        </div>
                        <span className={styles.percent}>{language.percent}%</span>
                      </div>
                    ))
                  )}
                </div>
                <div className={styles.tags}>
                  {technologies.length === 0 ? (
                    <span className={styles.muted}>Aucune technologie détectée.</span>
                  ) : (
                    technologies.map((technology) => (
                      <span key={`${technology.name}-${technology.category}`} className={styles.tag}>
                        {technology.name}
                        {technology.version ? ` ${technology.version}` : ""}
                      </span>
                    ))
                  )}
                </div>
              </Card>

              <Card title="Dernières analyses" subtitle="Historique des exécutions d'ingestion">
                <div className={styles.runs}>
                  {(project?.rag || latestRun) && (
                    <div className={styles.runItem}>
                      <span className={styles.runDot} />
                      <div>
                        <strong>Indexation RAG</strong>
                        <span>
                          {formatNumber(project?.rag?.chunks)} chunks · {formatNumber(project?.rag?.files)} fichiers
                        </span>
                      </div>
                      <span className={styles.runDate}>
                        {project?.rag?.indexed_at
                          ? formatDateTime(new Date(project.rag.indexed_at))
                          : "—"}
                      </span>
                    </div>
                  )}
                  {latestRun && (
                    <div className={styles.runItem}>
                      <span className={styles.runDot} />
                      <div>
                        <strong>Analyse du code</strong>
                        <span>
                          {latestRun.status} · {formatNumber(latestRun.symbols)} symboles
                        </span>
                      </div>
                      <span className={styles.runDate}>
                        {latestRun.finished_at ? formatDateTime(new Date(latestRun.finished_at)) : "—"}
                      </span>
                    </div>
                  )}
                  {!project?.rag && !latestRun && (
                    <EmptyState
                      title="Aucune analyse"
                      description="Lancez l'ingestion du projet pour voir l'historique."
                    />
                  )}
                </div>
                <div className={styles.shortcuts}>
                  <Link to="/architecture">
                    <Boxes size={15} /> Architecture <ArrowRight size={14} />
                  </Link>
                  <Link to="/code-analysis">
                    <ShieldAlert size={15} /> Analyse du code <ArrowRight size={14} />
                  </Link>
                  <Link to="/assistant">
                    <Terminal size={15} /> Assistant IA <ArrowRight size={14} />
                  </Link>
                </div>
              </Card>
            </section>

            <Card
              title="Findings et tickets récents"
              subtitle="Priorisez les problèmes détectés sur ce dépôt"
              headerAction={
                <Link className={styles.link} to="/issues">
                  Tous les tickets <ArrowRight size={14} />
                </Link>
              }
            >
              <div className={styles.issuesGrid}>
                <div>
                  <h3 className={styles.subheading}>Findings prioritaires</h3>
                  {findings.length === 0 ? (
                    <p className={styles.muted}>Aucun finding enregistré.</p>
                  ) : (
                    <ul className={styles.findingList}>
                      {findings.slice(0, 5).map((finding) => (
                        <li key={finding.id}>
                          <span className={`${styles.dot} ${styles[severityOf(finding)]}`} />
                          <div>
                            <strong>{finding.label ?? finding.model_name}</strong>
                            <span>{finding.file ?? finding.target_id ?? "cible inconnue"}</span>
                          </div>
                          <span>{Math.round(Number(finding.score || 0) * 100)}%</span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <h3 className={styles.subheading}>Tickets récents</h3>
                  {issues.length === 0 ? (
                    <p className={styles.muted}>Aucun ticket pour ce projet.</p>
                  ) : (
                    <ul className={styles.issueList}>
                      {issues.slice(0, 5).map((issue) => (
                        <li key={issue.id}>
                          <div>
                            <strong>{issue.title}</strong>
                            <span>{issue.kind ?? "non classé"} · {issue.status ?? "open"}</span>
                          </div>
                          <span className={styles.issueDate}>
                            {issue.created_at ? formatDateTime(new Date(issue.created_at)) : "—"}
                          </span>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
