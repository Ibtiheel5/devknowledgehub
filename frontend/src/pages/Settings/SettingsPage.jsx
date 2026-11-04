import { useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import { Download, MonitorCog, RefreshCw, RotateCcw, Server, SlidersHorizontal } from "lucide-react";
import { Topbar } from "../../components/layout";
import { useLayout } from "../../components/layout/LayoutContext";
import { Button, Card, Select, StatusPill } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { listProjects } from "../../services/projectApi";
import { downloadJson } from "../../utils/export";
import styles from "./SettingsPage.module.css";

const PREFERENCES_KEY = "dkh.preferences";

const DEFAULT_PREFERENCES = {
  density: "comfortable",
  showHints: true,
  reduceMotion: false
};

function readPreferences() {
  try {
    const raw = localStorage.getItem(PREFERENCES_KEY);
    return raw ? { ...DEFAULT_PREFERENCES, ...JSON.parse(raw) } : DEFAULT_PREFERENCES;
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export function SettingsPage() {
  const { connection, refreshHealth } = useOutletContext();
  const { collapsed, toggleCollapsed } = useLayout();
  const { activeRepo, setActiveRepo, knownRepos } = useRepo();
  const [projects, setProjects] = useState([]);
  const [preferences, setPreferences] = useState(readPreferences);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    listProjects()
      .then((result) => setProjects(Array.isArray(result) ? result : []))
      .catch(() => setProjects([]));
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
      setSavedAt(new Date());
    } catch {
      setSavedAt(null);
    }
    document.documentElement.dataset.density = preferences.density;
    document.documentElement.dataset.reduceMotion = preferences.reduceMotion ? "1" : "0";
  }, [preferences]);

  const repoOptions = useMemo(() => {
    const names = new Set([...knownRepos, ...projects.map((project) => project.name), activeRepo]);
    return [...names].filter(Boolean).sort();
  }, [knownRepos, projects, activeRepo]);

  const update = (key, value) => setPreferences((current) => ({ ...current, [key]: value }));

  const reset = () => {
    setPreferences(DEFAULT_PREFERENCES);
    toggleCollapsed();
  };

  const exportConfig = () =>
    downloadJson("devknowledgehub-settings.json", {
      active_repo: activeRepo,
      preferences,
      known_repos: repoOptions,
      exported_at: new Date().toISOString()
    });

  return (
    <div className={styles.page}>
      <Topbar
        title="Paramètres"
        subtitle="Préférences de l'espace de travail, dépôt actif et état de la plateforme."
        breadcrumbs={<span>DevKnowledgeHub / Paramètres</span>}
        onRefresh={refreshHealth}
      />

      <div className={styles.content}>
        <section className={styles.gridTwo}>
          <Card
            title="Espace de travail"
            subtitle="Choisissez le dépôt actif utilisé par les pages d'analyse."
            headerAction={<SlidersHorizontal size={17} />}
          >
            <label className={styles.field}>
              <span>Dépôt actif</span>
              <Select
                value={activeRepo}
                onChange={(event) => setActiveRepo(event.target.value)}
              >
                {repoOptions.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </Select>
            </label>

            <label className={styles.field}>
              <span>Densité d'affichage</span>
              <Select
                value={preferences.density}
                onChange={(event) => update("density", event.target.value)}
              >
                <option value="comfortable">Confortable</option>
                <option value="compact">Compacte</option>
              </Select>
            </label>

            <label className={styles.switch}>
              <input
                type="checkbox"
                checked={preferences.showHints}
                onChange={(event) => update("showHints", event.target.checked)}
              />
              <span>
                <strong>Afficher les textes d'aide</strong>
                <small>Descriptions et conseils dans les pages.</small>
              </span>
            </label>

            <label className={styles.switch}>
              <input
                type="checkbox"
                checked={preferences.reduceMotion}
                onChange={(event) => update("reduceMotion", event.target.checked)}
              />
              <span>
                <strong>Réduire les animations</strong>
                <small>Désactive les transitions non essentielles.</small>
              </span>
            </label>

            <label className={styles.switch}>
              <input type="checkbox" checked={collapsed} onChange={toggleCollapsed} />
              <span>
                <strong>Replier la navigation</strong>
                <small>Mode compact de la barre latérale sur desktop.</small>
              </span>
            </label>

            <div className={styles.actions}>
              <Button variant="outline" onClick={reset}>
                <RotateCcw size={14} /> Réinitialiser
              </Button>
              <Button variant="primary" onClick={exportConfig}>
                <Download size={14} /> Exporter la configuration
              </Button>
            </div>
            {savedAt && <p className={styles.saved}>Préférences enregistrées localement.</p>}
          </Card>

          <Card
            title="État de la plateforme"
            subtitle="Connexion à l'API, à Neo4j et au stockage des données."
            headerAction={<Server size={17} />}
          >
            <div className={styles.statusRow}>
              <span>Connexion backend</span>
              <StatusPill
                status={connection?.status === "ok" ? "ok" : connection?.status === "warn" ? "warn" : connection?.status === "error" ? "error" : "loading"}
                label={connection?.label ?? "Vérification..."}
              />
            </div>

            <dl className={styles.facts}>
              <div>
                <dt>API</dt>
                <dd>FastAPI · port 8000</dd>
              </div>
              <div>
                <dt>Graphe</dt>
                <dd>Neo4j</dd>
              </div>
              <div>
                <dt>Données</dt>
                <dd>PostgreSQL</dd>
              </div>
              <div>
                <dt>Ancienneté</dt>
                <dd>Frontend React 19 + Vite</dd>
              </div>
            </dl>

            <div className={styles.actions}>
              <Button variant="outline" onClick={refreshHealth}>
                <RefreshCw size={14} /> Vérifier la connexion
              </Button>
            </div>

            <div className={styles.infoBox}>
              <MonitorCog size={18} />
              <p>
                Les préférences restent dans ce navigateur. Aucune clé, aucun secret ni contenu de
                code n'est exporté par cette page.
              </p>
            </div>
          </Card>
        </section>

        <Card title="Dépôts connus" subtitle={`${repoOptions.length} dépôt(s) configuré(s)`}>
          <ul className={styles.repoList}>
            {repoOptions.map((name) => (
              <li key={name} className={name === activeRepo ? styles.activeRepo : undefined}>
                <button type="button" onClick={() => setActiveRepo(name)}>
                  <strong>{name}</strong>
                  <span>{name === activeRepo ? "Dépôt actif" : "Activer ce dépôt"}</span>
                </button>
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </div>
  );
}
