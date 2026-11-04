import { useCallback, useEffect, useMemo, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { FolderGit2, Grid3X3, LayoutList, Plus, Search } from "lucide-react";
import { Topbar } from "../../components/layout";
import {
  Button,
  Card,
  DataTable,
  EmptyState,
  StatusPill,
  TextField
} from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { analyzeRepository } from "../../services/graphApi";
import {
  createProject,
  getProjectStatus,
  ingestProject,
  ingestProjectZip,
  listProjects
} from "../../services/projectApi";
import styles from "./ProjectsPage.module.css";

function nameFromUrl(url) {
  const last = url.trim().replace(/\/+$/, "").split("/").pop() || "";
  return last.replace(/\.git$/, "");
}

function nameFromZip(file) {
  return file?.name?.replace(/\.zip$/i, "") || "";
}

function statusTone(status) {
  if (status === "ready") return "ok";
  if (status === "failed") return "error";
  if (status === "indexing" || status === "pending") return "warn";
  return "idle";
}

async function waitForIngestion(name, onProgress) {
  for (let attempt = 0; attempt < 60; attempt += 1) {
    await new Promise((resolve) => setTimeout(resolve, 2000));
    const status = await getProjectStatus(name);
    onProgress(status);
    if (status.status === "ready" || status.status === "failed") return status;
  }
  throw new Error("Délai d'ingestion dépassé. Vérifiez l'état du projet dans la liste.");
}

function ProjectCard({ project, active, onOpen }) {
  const languages = Object.keys(project.languages ?? {});
  return (
    <article className={`${styles.projectCard} ${active ? styles.projectCardActive : ""}`}>
      <header className={styles.projectHeader}>
        <div className={styles.projectTitleWrap}>
          <span className={styles.projectIcon}>
            <FolderGit2 size={18} />
          </span>
          <div>
            <h3>{project.name}</h3>
            {project.git_url && <p>{project.git_url}</p>}
          </div>
        </div>
        <StatusPill status={statusTone(project.status)} label={project.status} />
      </header>
      <div className={styles.projectMeta}>
        <span>{languages.length ? languages.join(", ") : "Langages non détectés"}</span>
        <span>Type : {project.project_type ?? "git"}</span>
      </div>
      <footer className={styles.projectFooter}>
        <span className={styles.projectHint}>
          {active ? "Dépôt actif" : "Cliquer pour définir comme actif"}
        </span>
        <Button variant="outline" onClick={() => onOpen(project)}>
          Ouvrir
        </Button>
      </footer>
    </article>
  );
}

export function ProjectsPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { activeRepo, setActiveRepo } = useRepo();
  const [gitUrl, setGitUrl] = useState("");
  const [zipFile, setZipFile] = useState(null);
  const [repoName, setRepoName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);
  const [view, setView] = useState("grid");
  const [query, setQuery] = useState("");
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingImport, setLoadingImport] = useState(false);
  const [loadingProjects, setLoadingProjects] = useState(true);
  const [summary, setSummary] = useState(null);
  const [projectStatus, setProjectStatus] = useState(null);
  const [projects, setProjects] = useState([]);
  const [error, setError] = useState(null);

  const effectiveName = (
    nameTouched ? repoName : gitUrl ? nameFromUrl(gitUrl) : nameFromZip(zipFile)
  ).trim();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const q = params.get("search") || "";
    if (q) setQuery(q);
  }, [location.search]);

  const loadProjects = useCallback(async () => {
    setLoadingProjects(true);
    try {
      const items = await listProjects();
      setProjects(Array.isArray(items) ? items : []);
    } catch {
      setProjects([]);
    } finally {
      setLoadingProjects(false);
    }
  }, []);

  useEffect(() => {
    loadProjects();
  }, [loadProjects]);

  const filteredProjects = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return projects;
    return projects.filter((project) =>
      [project.name, project.git_url, ...(Object.keys(project.languages ?? {}))]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(q)
    );
  }, [projects, query]);

  const onUrlChange = (event) => {
    setGitUrl(event.target.value);
    if (event.target.value) setZipFile(null);
    if (!nameTouched) setRepoName(nameFromUrl(event.target.value));
  };

  const onZipChange = (event) => {
    const file = event.target.files?.[0] ?? null;
    setZipFile(file);
    if (file) {
      setGitUrl("");
      if (!nameTouched) setRepoName(nameFromZip(file));
    }
  };

  const handleAnalyze = async () => {
    if (!gitUrl.trim()) return;
    setLoadingAnalyze(true);
    setError(null);
    setSummary(null);
    try {
      const response = await analyzeRepository(gitUrl.trim());
      setSummary(response.summary);
    } catch (err) {
      setError(err);
    } finally {
      setLoadingAnalyze(false);
    }
  };

  const handleImport = async () => {
    if ((!gitUrl.trim() && !zipFile) || !effectiveName) return;
    setLoadingImport(true);
    setError(null);
    setProjectStatus(null);
    try {
      await createProject(effectiveName, gitUrl.trim() || null, zipFile ? "zip" : "git");
      setActiveRepo(effectiveName);
      if (zipFile) {
        await ingestProjectZip(effectiveName, zipFile);
      } else {
        await ingestProject(effectiveName, gitUrl.trim());
      }
      const finalStatus = await waitForIngestion(effectiveName, setProjectStatus);
      setProjectStatus(finalStatus);
      await loadProjects();
      if (finalStatus.status === "ready") {
        navigate("/architecture");
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoadingImport(false);
    }
  };

  const openProject = (project) => {
    setActiveRepo(project.name);
    navigate("/project/overview");
  };

  const columns = [
    {
      key: "name",
      label: "Projet",
      render: (project) => (
        <div>
          <strong>{project.name}</strong>
          {project.git_url && <p className={styles.muted}>{project.git_url}</p>}
        </div>
      )
    },
    {
      key: "status",
      label: "État",
      render: (project) => <StatusPill status={statusTone(project.status)} label={project.status} />
    },
    { key: "project_type", label: "Type", render: (project) => project.project_type ?? "—" },
    {
      key: "languages",
      label: "Langages",
      render: (project) => Object.keys(project.languages ?? {}).join(", ") || "—"
    },
    {
      key: "actions",
      label: "",
      align: "right",
      render: (project) => (
        <Button
          variant="ghost"
          onClick={() => {
            setActiveRepo(project.name);
            navigate("/project/overview");
          }}
        >
          Ouvrir
        </Button>
      )
    }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="Projets"
        subtitle="Gérez, importez et analysez vos dépôts logiciels."
        breadcrumbs={<span>DevKnowledgeHub / Projets</span>}
        actions={
          <>
            <Button variant="outline" onClick={loadProjects} loading={loadingProjects}>
              Actualiser
            </Button>
            <Button variant="primary" onClick={() => window.scrollTo({ top: 0, behavior: "smooth" })}>
              <Plus size={16} />
              Importer un dépôt
            </Button>
          </>
        }
        onRefresh={loadProjects}
        refreshing={loadingProjects}
      />

      <div className={styles.content}>
        <Card title="Importer un dépôt" subtitle="Git URL ou ZIP (aperçu disponible) · Appel backend si disponible">
          <div className={styles.importGrid}>
            <div className={styles.form}>
              <TextField
                label="URL Git"
                placeholder="https://github.com/owner/repo.git"
                value={gitUrl}
                onChange={onUrlChange}
              />
              <label className={styles.fileField}>
                <span>Archive ZIP</span>
                <input type="file" accept=".zip,application/zip" onChange={onZipChange} />
                <small>{zipFile ? zipFile.name : "Sélectionnez un fichier ZIP (200 Mo maximum)."}</small>
              </label>
              <TextField
                label="Nom du projet"
                hint="Identifiant utilisé par le graphe, RAG et les agents."
                value={nameTouched ? repoName : effectiveName}
                onChange={(event) => {
                  setNameTouched(true);
                  setRepoName(event.target.value);
                }}
              />
              <div className={styles.actions}>
                <Button variant="primary" onClick={handleImport} loading={loadingImport} disabled={(!gitUrl.trim() && !zipFile) || !effectiveName}>
                  {loadingImport ? "Ingestion en cours..." : "Importer et indexer"}
                </Button>
                <Button variant="outline" onClick={handleAnalyze} loading={loadingAnalyze} disabled={!gitUrl.trim()}>
                  Aperçu seulement
                </Button>
              </div>
            </div>
            <div className={styles.preview}>
              <h3>Résumé de l'import</h3>
              <p>Les résultats réels proviennent du backend. Si indisponible, un état explicite est affiché.</p>
              {error && <p className={styles.error}>{error.message}</p>}
              {summary && (
                <div className={styles.kv}>
                  <span>Fichiers analysés</span>
                  <strong>{summary.files_parsed}</strong>
                  <span>Symboles</span>
                  <strong>{summary.symbols}</strong>
                  <span>Imports</span>
                  <strong>{summary.imports}</strong>
                  <span>Appels</span>
                  <strong>{summary.calls}</strong>
                </div>
              )}
              {projectStatus && (
                <div className={styles.statusBlock}>
                  <StatusPill status={statusTone(projectStatus.status)} label={projectStatus.status} />
                  {projectStatus.latest_run && (
                    <p>
                      {projectStatus.latest_run.files} fichiers · {projectStatus.latest_run.chunks} chunks RAG ·{" "}
                      {projectStatus.latest_run.symbols} symboles
                    </p>
                  )}
                  {projectStatus.error && <p className={styles.error}>{projectStatus.error}</p>}
                </div>
              )}
              {!summary && !projectStatus && !error && (
                <EmptyState title="Aucun aperçu" description="Lancez un aperçu ou un import pour voir les métriques." />
              )}
            </div>
          </div>
        </Card>

        <Card
          title="Liste des projets"
          subtitle={`${filteredProjects.length} projet(s) affiché(s) · ${projects.length} au total · actif : ${activeRepo}`}
          headerAction={
            <div className={styles.listActions}>
              <div className={styles.searchWrap}>
                <Search size={16} />
                <input
                  type="search"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder="Rechercher un projet..."
                />
              </div>
              <div className={styles.viewToggle}>
                <button type="button" className={view === "grid" ? styles.active : ""} onClick={() => setView("grid")} aria-label="Vue grille">
                  <Grid3X3 size={16} />
                </button>
                <button type="button" className={view === "list" ? styles.active : ""} onClick={() => setView("list")} aria-label="Vue liste">
                  <LayoutList size={16} />
                </button>
              </div>
            </div>
          }
        >
          {view === "grid" ? (
            <div className={styles.grid}>
              {filteredProjects.map((project) => (
                <ProjectCard key={project.id || project.name} project={project} active={project.name === activeRepo} onOpen={openProject} />
              ))}
              {filteredProjects.length === 0 && (
                <EmptyState
                  title={loadingProjects ? "Chargement..." : "Aucun projet trouvé"}
                  description={loadingProjects ? "Récupération des projets." : "Importez votre premier dépôt ou ajustez le filtre."}
                />
              )}
            </div>
          ) : (
            <DataTable
              columns={columns}
              data={filteredProjects}
              rowKey="id"
              emptyState={
                <EmptyState
                  title={loadingProjects ? "Chargement..." : "Aucun projet trouvé"}
                  description={loadingProjects ? "Récupération des projets." : "Importez votre premier dépôt ou ajustez le filtre."}
                />
              }
            />
          )}
        </Card>
      </div>
    </div>
  );
}
