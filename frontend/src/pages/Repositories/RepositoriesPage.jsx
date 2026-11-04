import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
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
import styles from "./RepositoriesPage.module.css";

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

export function RepositoriesPage() {
  const navigate = useNavigate();
  const { activeRepo, setActiveRepo } = useRepo();
  const [gitUrl, setGitUrl] = useState("");
  const [zipFile, setZipFile] = useState(null);
  const [repoName, setRepoName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);
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
      render: (project) => (
        <StatusPill status={statusTone(project.status)} label={project.status} />
      )
    },
    { key: "project_type", label: "Type", render: (project) => project.project_type ?? "—" },
    {
      key: "languages",
      label: "Langages",
      render: (project) =>
        Object.keys(project.languages ?? {}).join(", ") || "—"
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
            navigate("/architecture");
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
        title="Dépôts"
        subtitle="Importez un projet : analyse, documentation, tickets et findings sont indexés."
        breadcrumbs={<span>DevKnowledgeHub / Dépôts</span>}
        onRefresh={loadProjects}
        refreshing={loadingProjects}
      />

      <div className={styles.content}>
        <Card title="Importer un projet" subtitle="Collez l'URL Git du dépôt à analyser">
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
              hint="Utilisé pour retrouver le projet dans le graphe et avec l'agent."
              value={nameTouched ? repoName : effectiveName}
              onChange={(event) => {
                setNameTouched(true);
                setRepoName(event.target.value);
              }}
            />
            <div className={styles.actions}>
              <Button
                variant="primary"
                onClick={handleImport}
                loading={loadingImport}
                disabled={(!gitUrl.trim() && !zipFile) || !effectiveName}
              >
                {loadingImport ? "Ingestion en cours..." : "Importer et indexer"}
              </Button>
              <Button
                variant="outline"
                onClick={handleAnalyze}
                loading={loadingAnalyze}
                disabled={!gitUrl.trim()}
              >
                Aperçu seulement
              </Button>
            </div>
          </div>

          {error && <p className={styles.error}>{error.message}</p>}

          {summary && (
            <div className={styles.summary}>
              <span>Fichiers : {summary.files_parsed}</span>
              <span>Symboles : {summary.symbols}</span>
              <span>Imports : {summary.imports}</span>
              <span>Appels : {summary.calls}</span>
            </div>
          )}

          {projectStatus && (
            <div className={styles.summary}>
              <StatusPill status={statusTone(projectStatus.status)} label={projectStatus.status} />
              {projectStatus.latest_run && (
                <span>
                  {projectStatus.latest_run.files} fichiers · {projectStatus.latest_run.chunks}{" "}
                  extraits RAG · {projectStatus.latest_run.symbols} symboles
                </span>
              )}
              {projectStatus.error && <span className={styles.error}>{projectStatus.error}</span>}
            </div>
          )}
        </Card>

        <Card
          title="Projets"
          subtitle={`${projects.length} projet(s) · actif : ${activeRepo}`}
        >
          <DataTable
            columns={columns}
            data={projects}
            rowKey="id"
            emptyState={
              <EmptyState
                title={loadingProjects ? "Chargement…" : "Aucun projet"}
                description={
                  loadingProjects
                    ? "Récupération des projets."
                    : "Importez un dépôt Git pour créer votre premier projet."
                }
              />
            }
          />
        </Card>
      </div>
    </div>
  );
}
