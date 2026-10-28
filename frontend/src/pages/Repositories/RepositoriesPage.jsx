import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Topbar } from "../../components/layout";
import { Card, Button, TextField } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { analyzeRepository, buildGraph } from "../../services/graphApi";
import { indexRepository } from "../../services/ragApi";
import styles from "./RepositoriesPage.module.css";

function nameFromUrl(url) {
  const last = url.trim().replace(/\/+$/, "").split("/").pop() || "";
  return last.replace(/\.git$/, "");
}

export function RepositoriesPage() {
  const navigate = useNavigate();
  const { activeRepo, setActiveRepo, knownRepos } = useRepo();
  const [gitUrl, setGitUrl] = useState("");
  const [repoName, setRepoName] = useState("");
  const [nameTouched, setNameTouched] = useState(false);
  const [loadingAnalyze, setLoadingAnalyze] = useState(false);
  const [loadingBuild, setLoadingBuild] = useState(false);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [buildResult, setBuildResult] = useState(null);
  const [ragResult, setRagResult] = useState(null);

  const effectiveName = (nameTouched ? repoName : nameFromUrl(gitUrl)).trim();

  const onUrlChange = (e) => {
    setGitUrl(e.target.value);
    if (!nameTouched) setRepoName(nameFromUrl(e.target.value));
  };

  const handleAnalyze = async () => {
    if (!gitUrl.trim()) return;
    setLoadingAnalyze(true);
    setError(null);
    setSummary(null);
    setBuildResult(null);
    setRagResult(null);
    try {
      const res = await analyzeRepository(gitUrl.trim());
      setSummary(res.summary);
    } catch (err) {
      setError(err);
    } finally {
      setLoadingAnalyze(false);
    }
  };

  // Import = cloner + analyser + construire le graphe, puis ouvrir la visualisation.
  const handleImport = async () => {
    if (!gitUrl.trim() || !effectiveName) return;
    setLoadingBuild(true);
    setError(null);
    setBuildResult(null);
    setRagResult(null);
    let graphBuilt = false;
    try {
      const res = await buildGraph(effectiveName, gitUrl.trim());
      setBuildResult(res);
      setActiveRepo(effectiveName);
      graphBuilt = true;
      const indexed = await indexRepository(effectiveName, gitUrl.trim());
      setRagResult(indexed);
      navigate("/knowledge-graph");
    } catch (err) {
      setError(
        graphBuilt
          ? new Error(`Le graphe est construit, mais l'indexation RAG a échoué : ${err.message}`)
          : err
      );
    } finally {
      setLoadingBuild(false);
    }
  };

  return (
    <div className={styles.page}>
      <Topbar
        title="Dépôts"
        subtitle="Importez un projet : le graphe et l'index de recherche sont construits."
        breadcrumbs={<span>DevKnowledgeHub / Dépôts</span>}
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
            <TextField
              label="Nom du projet"
              hint="Utilisé pour retrouver le projet dans le graphe et avec l'agent."
              value={nameTouched ? repoName : effectiveName}
              onChange={(e) => {
                setNameTouched(true);
                setRepoName(e.target.value);
              }}
            />
            <div className={styles.actions}>
              <Button
                variant="primary"
                onClick={handleImport}
                loading={loadingBuild}
                disabled={!gitUrl.trim() || !effectiveName}
              >
                {loadingBuild ? "Construction du graphe et indexation..." : "Importer le projet"}
              </Button>
              <Button variant="outline" onClick={handleAnalyze} loading={loadingAnalyze} disabled={!gitUrl.trim()}>
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
          {buildResult && (
            <p className={styles.success}>
              Graphe : {buildResult.files} fichiers, {buildResult.symbols} symboles,{" "}
              {buildResult.calls_resolved} appels résolus.
              {ragResult && ` Index RAG : ${ragResult.chunks} extraits issus de ${ragResult.files} fichiers.`}
            </p>
          )}
        </Card>

        <Card title="Projets" subtitle="Choisissez le projet actif pour le graphe et l'agent">
          <div className={styles.repoList}>
            {knownRepos.map((repo) => (
              <div key={repo} className={`${styles.repoItem} ${repo === activeRepo ? styles.active : ""}`}>
                <div>
                  <strong>{repo}</strong>
                  <span>{repo === activeRepo ? "Projet actif" : "Disponible"}</span>
                </div>
                <div className={styles.actions}>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setActiveRepo(repo);
                      navigate("/knowledge-graph");
                    }}
                  >
                    Voir le graphe
                  </Button>
                  <Button
                    variant="ghost"
                    onClick={() => {
                      setActiveRepo(repo);
                      navigate("/copilot");
                    }}
                  >
                    Parler à l'agent
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
