import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  Activity,
  ArrowRight,
  Bot,
  Boxes,
  CircleAlert,
  FolderKanban,
  GitBranch,
  Network,
  FileCode2,
  BookOpen,
  Database,
  BrainCircuit,
  ShieldAlert,
  Sparkles
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";
import { Topbar } from "../../components/layout";
import { Button, Card, CardStat, EmptyState } from "../../components/ui";
import { ForceGraph } from "../../components/graph";
import { useRepo } from "../../store/RepoContext";
import {
  getRepoCalls,
  getRepoStats,
  getRepoSymbols
} from "../../services/graphApi";
import { getProjectFindings, listProjects } from "../../services/projectApi";
import { getAgentRuns, getModels, getMonitoring } from "../../services/mlopsApi";
import { formatDateTime, formatNumber } from "../../utils/format";
import styles from "./DashboardPage.module.css";

const SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"];
const SEVERITY_COLORS = {
  critical: "#8f2f2f",
  high: "#b94a48",
  medium: "#b7791f",
  low: "#4f7c3e",
  info: "#8c6a4f"
};

function severityOf(finding) {
  const raw = String(
    finding?.payload?.severity || finding?.label || finding?.model_name || "info"
  ).toLowerCase();
  if (raw.includes("critical")) return "critical";
  if (raw.includes("high") || raw.includes("vuln")) return "high";
  if (raw.includes("medium") || raw.includes("smell") || raw.includes("duplicate")) return "medium";
  if (raw.includes("low")) return "low";
  return "info";
}

function progressForStatus(status) {
  if (status === "ready") return 100;
  if (status === "indexing") return 62;
  if (status === "pending") return 24;
  if (status === "failed") return 100;
  return 10;
}

function statusTone(status) {
  if (status === "ready") return styles.ok;
  if (status === "failed") return styles.errorTone;
  return styles.warn;
}

function ProjectRow({ project, active, onOpen }) {
  const languages = Object.keys(project.languages ?? {});
  const technologies = (project.technologies ?? []).slice(0, 3).map((item) => item.name);
  const progress = progressForStatus(project.status);
  return (
    <button type="button" className={styles.projectRow} onClick={() => onOpen(project)}>
      <div className={styles.projectMain}>
        <span className={styles.projectIcon}>
          <FolderKanban size={17} />
        </span>
        <div className={styles.projectText}>
          <strong>{project.name}</strong>
          <span>
            {languages.length ? languages.join(" · ") : "Langages non détectés"}
            {technologies.length ? ` · ${technologies.join(", ")}` : ""}
          </span>
        </div>
      </div>
      <div className={styles.projectMeta}>
        <span className={`${styles.status} ${statusTone(project.status)}`}>{project.status}</span>
        <span>
          {project.updated_at ? formatDateTime(new Date(project.updated_at)) : "Date inconnue"}
        </span>
        {active && <span className={styles.activeTag}>Actif</span>}
      </div>
      <div className={styles.progressWrap} aria-label={`Progression ${progress}%`}>
        <span style={{ width: `${progress}%` }} />
      </div>
    </button>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { activeRepo, setActiveRepo } = useRepo();
  const [projects, setProjects] = useState([]);
  const [stats, setStats] = useState(null);
  const [symbols, setSymbols] = useState([]);
  const [calls, setCalls] = useState([]);
  const [findings, setFindings] = useState([]);
  const [models, setModels] = useState([]);
  const [runs, setRuns] = useState(null);
  const [monitoring, setMonitoring] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [updatedAt, setUpdatedAt] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    const results = await Promise.allSettled([
      listProjects(),
      getRepoStats(activeRepo),
      getRepoSymbols(activeRepo, 24),
      getRepoCalls(activeRepo, 80),
      getProjectFindings(activeRepo, null, 200),
      getModels(activeRepo),
      getAgentRuns(50),
      getMonitoring(activeRepo, 7)
    ]);
    const [projectsResult, statsResult, symbolsResult, callsResult, findingsResult, modelsResult, runsResult, monitoringResult] = results;
    if (projectsResult.status === "fulfilled") {
      const list = Array.isArray(projectsResult.value) ? projectsResult.value : [];
      setProjects(list);
      if (list.length > 0 && !list.some((project) => project.name === activeRepo)) {
        setActiveRepo(list[0].name);
        setLoading(false);
        return;
      }
    }
    if (statsResult.status === "fulfilled") setStats(statsResult.value);
    if (symbolsResult.status === "fulfilled") {
      setSymbols(Array.isArray(symbolsResult.value) ? symbolsResult.value : []);
    }
    if (callsResult.status === "fulfilled") {
      setCalls(Array.isArray(callsResult.value) ? callsResult.value : []);
    }
    if (findingsResult.status === "fulfilled") {
      setFindings(Array.isArray(findingsResult.value.findings) ? findingsResult.value.findings : []);
    }
    if (modelsResult.status === "fulfilled") {
      setModels(Array.isArray(modelsResult.value.models) ? modelsResult.value.models : []);
    }
    if (runsResult.status === "fulfilled") setRuns(runsResult.value);
    if (monitoringResult.status === "fulfilled") setMonitoring(monitoringResult.value);
    const rejected = results.find((result) => result.status === "rejected");
    if (rejected) setError(rejected.reason);
    setUpdatedAt(new Date());
    setLoading(false);
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const activeProject = projects.find((project) => project.name === activeRepo);

  const severityData = useMemo(() => {
    const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const finding of findings) counts[severityOf(finding)] += 1;
    return SEVERITY_ORDER.map((key) => ({ key, name: key, value: counts[key] }));
  }, [findings]);

  const modelData = useMemo(
    () =>
      models.slice(0, 5).map((model) => ({
        name: model.model_name?.replace(/_/g, " ") ?? "modèle",
        score: Math.round((Number(model.avg_score) || 0) * 100),
        predictions: model.predictions ?? 0
      })),
    [models]
  );

  const readyProjects = projects.filter((project) => project.status === "ready").length;
  const progress = projects.length ? Math.round((readyProjects / projects.length) * 100) : 0;

  const recentFindings = useMemo(
    () =>
      [...findings]
        .sort((a, b) => Number(b.score || 0) - Number(a.score || 0))
        .slice(0, 5),
    [findings]
  );

  return (
    <div className={styles.page}>
      <Topbar
        title="DevKnowledgeHub"
        subtitle="Plateforme d'intelligence logicielle : analyse de dépôts, graphe de connaissances, RAG et agents IA."
        breadcrumbs={<span>DevKnowledgeHub / Tableau de bord</span>}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate("/projects")}>
              Explorer les projets
            </Button>
            <Button variant="primary" onClick={() => navigate("/projects")}>
              Importer un dépôt
            </Button>
          </>
        }
        onRefresh={load}
        refreshing={loading}
        showHeading={false}
      />

      <div className={styles.content}>
        <section className={styles.hero} aria-labelledby="dashboard-hero-title">
          <div className={styles.heroCopy}>
            <div className={styles.heroEyebrow}>
              <Sparkles size={14} />
              Intelligence logicielle pour développeurs
            </div>
            <h1 id="dashboard-hero-title">DevKnowledgeHub</h1>
            <h2>AI-powered Developer Knowledge &amp; Software Repository Intelligence Platform</h2>
            <p>
              Analysez, comprenez et explorez vos projets avec l’IA : code, documentation,
              tickets et dépendances réunis dans un même espace.
            </p>
            <div className={styles.heroTags} aria-label="Technologies utilisées">
              {[
                ["NLP avancé", BrainCircuit],
                ["Code Intelligence", FileCode2],
                ["GraphRAG", Network],
                ["Agentic RAG", Sparkles],
                ["ML / DL", Boxes],
                ["FastAPI", GitBranch],
                ["React", GitBranch],
                ["Neo4j", Database],
                ["Vector DB", Database]
              ].map(([label, Icon]) => (
                <span key={label} className={styles.heroTag}>
                  <Icon size={13} />
                  {label}
                </span>
              ))}
            </div>
          </div>
          <div className={styles.heroVisual} aria-hidden="true">
            <div className={`${styles.heroOrbit} ${styles.heroOrbitOne}`} />
            <div className={`${styles.heroOrbit} ${styles.heroOrbitTwo}`} />
            <div className={`${styles.heroNode} ${styles.heroNodeMain}`}>
              <Network size={30} />
            </div>
            <div className={`${styles.heroNode} ${styles.heroNodeCode}`}>
              <FileCode2 size={20} />
            </div>
            <div className={`${styles.heroNode} ${styles.heroNodeRepo}`}>
              <GitBranch size={20} />
            </div>
            <div className={`${styles.heroNode} ${styles.heroNodeDocs}`}>
              <BookOpen size={20} />
            </div>
          </div>
        </section>

        <div className={styles.dashboardActions}>
          <div>
            <span className={styles.dashboardKicker}>Tableau de bord</span>
            <p>Un aperçu de vos dépôts, analyses et agents IA.</p>
          </div>
          <div className={styles.dashboardActionButtons}>
            <Button variant="outline" onClick={() => navigate("/projects")}>
              Explorer les projets
            </Button>
            <Button variant="primary" onClick={() => navigate("/projects")}>
              Importer un dépôt
            </Button>
            <Button variant="outline" onClick={load} loading={loading}>
              Actualiser
            </Button>
          </div>
        </div>

        {error && (
          <div className={styles.banner}>
            <CircleAlert size={17} />
            <span>Certaines données sont indisponibles : {error.message}</span>
          </div>
        )}

        <section className={styles.kpis}>
          <CardStat
            label="Projets suivis"
            value={formatNumber(projects.length)}
            icon={<FolderKanban size={18} />}
            hint={`${readyProjects} prêt(s) · actif : ${activeRepo}`}
          />
          <CardStat
            label="Modèles ML / DL"
            value={formatNumber(models.length)}
            icon={<Boxes size={18} />}
            hint={`${monitoring?.predictions?.total ?? 0} prédictions sur 7 jours`}
          />
          <CardStat
            label="Findings code"
            value={formatNumber(findings.length)}
            icon={<ShieldAlert size={18} />}
            hint={`${severityData[0].value} critiques · ${severityData[1].value} élevés`}
          />
          <CardStat
            label="Progression d'analyse"
            value={`${loading ? "—" : progress}%`}
            icon={<Activity size={18} />}
            hint={`${formatNumber(stats?.files)} fichiers · ${formatNumber(stats?.symbols)} symboles`}
          />
        </section>

        <section className={styles.gridTwo}>
          <Card
            title="Projets récents"
            subtitle={`${projects.length} dépôt(s) suivis · ${activeProject?.status ?? "statut inconnu"}`}
            headerAction={
              <Link className={styles.link} to="/projects">
                Tout voir <ArrowRight size={14} />
              </Link>
            }
          >
            {projects.length === 0 ? (
              <EmptyState
                title={loading ? "Chargement..." : "Aucun projet"}
                description="Importez un dépôt Git pour démarrer l'analyse."
                action={
                  <Button variant="primary" onClick={() => navigate("/projects")}>
                    Importer un dépôt
                  </Button>
                }
              />
            ) : (
              <div className={styles.projectList}>
                {[activeProject, ...projects.filter((project) => project.name !== activeRepo)]
                  .filter(Boolean)
                  .slice(0, 4)
                  .map((project) => (
                    <ProjectRow
                      key={project.id || project.name}
                      project={project}
                      active={project.name === activeRepo}
                      onOpen={(item) => {
                        setActiveRepo(item.name);
                        navigate("/project/overview");
                      }}
                    />
                  ))}
              </div>
            )}
          </Card>

          <Card
            title="Aperçu du graphe de connaissances"
            subtitle={`${formatNumber(stats?.calls)} appels · ${formatNumber(stats?.imports)} imports`}
            headerAction={
              <Link className={styles.link} to="/architecture">
                Ouvrir le graphe <ArrowRight size={14} />
              </Link>
            }
          >
            <div className={styles.graphPreview}>
              {calls.length > 0 ? (
                <ForceGraph
                  calls={calls.slice(0, 45)}
                  selected={selectedNode}
                  onSelect={setSelectedNode}
                  compact
                />
              ) : (
                <EmptyState
                  title={loading ? "Chargement..." : "Graphe indisponible"}
                  description="Construisez le graphe pour voir les relations entre symboles."
                />
              )}
            </div>
          </Card>
        </section>

        <section className={styles.gridTwo}>
          <Card
            title="Qualité du code"
            subtitle="Répartition des findings par sévérité"
            headerAction={
              <Link className={styles.link} to="/code-analysis">
                Analyste <ArrowRight size={14} />
              </Link>
            }
          >
            {findings.length === 0 ? (
              <EmptyState
                title={loading ? "Chargement..." : "Aucun finding"}
                description="Les détecteurs n'ont pas encore produit de résultats pour ce dépôt."
              />
            ) : (
              <>
                <div className={styles.chart}>
                  <ResponsiveContainer width="100%" height={210}>
                    <BarChart data={severityData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={11} />
                      <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={11} width={28} />
                      <Tooltip
                        cursor={{ fill: "rgba(185,104,75,0.06)" }}
                        contentStyle={{
                          borderRadius: 10,
                          border: "1px solid var(--border)",
                          fontSize: 12
                        }}
                      />
                      <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                        {severityData.map((entry) => (
                          <Cell key={entry.key} fill={SEVERITY_COLORS[entry.key]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className={styles.severityLegend}>
                  {severityData.map((item) => (
                    <span key={item.key}>
                      <i style={{ background: SEVERITY_COLORS[item.key] }} />
                      {item.name} · {item.value}
                    </span>
                  ))}
                </div>
              </>
            )}
          </Card>

          <Card
            title="Performance des modèles"
            subtitle="Score moyen et volume de prédictions"
            headerAction={
              <Link className={styles.link} to="/models">
                Voir les modèles <ArrowRight size={14} />
              </Link>
            }
          >
            {modelData.length === 0 ? (
              <EmptyState
                title={loading ? "Chargement..." : "Aucun modèle"}
                description="Les modèles apparaîtront après les premières prédictions."
              />
            ) : (
              <>
                <div className={styles.chart}>
                  <ResponsiveContainer width="100%" height={210}>
                    <BarChart data={modelData} layout="vertical" margin={{ left: 8, right: 16 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="var(--border)" />
                      <XAxis type="number" domain={[0, 100]} tickLine={false} axisLine={false} fontSize={11} />
                      <YAxis
                        type="category"
                        dataKey="name"
                        width={120}
                        tickLine={false}
                        axisLine={false}
                        fontSize={11}
                      />
                      <Tooltip
                        formatter={(value) => [`${value}%`, "score moyen"]}
                        contentStyle={{
                          borderRadius: 10,
                          border: "1px solid var(--border)",
                          fontSize: 12
                        }}
                      />
                      <Bar dataKey="score" fill="var(--brand)" radius={[0, 6, 6, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className={styles.modelList}>
                  {models.slice(0, 4).map((model) => (
                    <div key={`${model.model_name}-${model.model_version}`} className={styles.modelRow}>
                      <strong>{model.model_name}</strong>
                      <span>{formatNumber(model.predictions)} prédictions</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </Card>
        </section>

        <section className={styles.gridTwo}>
          <Card
            title="Findings récents"
            subtitle="Résultats des détecteurs statiques et ML"
            headerAction={
              <Link className={styles.link} to="/code-analysis">
                Tout inspecter <ArrowRight size={14} />
              </Link>
            }
          >
            {recentFindings.length === 0 ? (
              <EmptyState
                title={loading ? "Chargement..." : "Aucun finding"}
                description="Aucun résultat disponible pour le moment."
              />
            ) : (
              <ul className={styles.findingList}>
                {recentFindings.map((finding) => (
                  <li key={finding.id}>
                    <span className={`${styles.severityDot} ${styles[severityOf(finding)]}`} />
                    <div>
                      <strong>{finding.label ?? finding.model_name ?? "Finding"}</strong>
                      <span>{finding.file ?? finding.target_id ?? "cible inconnue"}</span>
                    </div>
                    <span className={styles.score}>
                      {Math.round(Number(finding.score || 0) * 100)}%
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card
            title="Assistant IA"
            subtitle={`Copilot RAG · ${runs?.summary?.latest_model ?? "modèle local"}`}
            headerAction={
              <Link className={styles.link} to="/assistant">
                Ouvrir l'assistant <ArrowRight size={14} />
              </Link>
            }
          >
            <div className={styles.assistantPreview}>
              <span className={styles.assistantIcon}>
                <Bot size={22} />
              </span>
              <p>
                Posez une question sur l'architecture, les dépendances ou la sécurité du dépôt
                <strong> {activeRepo}</strong>.
              </p>
              <div className={styles.suggestions}>
                {[
                  "Explique l'architecture du projet.",
                  "Où est implémentée l'authentification ?",
                  "Quels fichiers dois-je inspecter ?"
                ].map((question) => (
                  <button
                    key={question}
                    type="button"
                    onClick={() => navigate(`/assistant?q=${encodeURIComponent(question)}`)}
                  >
                    <Sparkles size={13} />
                    {question}
                  </button>
                ))}
              </div>
              <div className={styles.assistantMeta}>
                <span>
                  <GitBranch size={14} /> {formatNumber(runs?.summary?.total)} exécutions d'agents
                </span>
                <span>
                  <Activity size={14} /> {monitoring?.agents?.success_rate ? `${Math.round(monitoring.agents.success_rate * 100)}% de succès` : "n/a"}
                </span>
              </div>
            </div>
          </Card>
        </section>

        {updatedAt && (
          <p className={styles.updated}>Dernière actualisation : {formatDateTime(updatedAt)}</p>
        )}
      </div>
    </div>
  );
}
