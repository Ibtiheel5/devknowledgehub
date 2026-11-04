import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Topbar } from "../../components/layout";
import { Button, Card, CardStat, EmptyState } from "../../components/ui";
import { getAgentRuns } from "../../services/mlopsApi";
import { getAgentCatalog, runSpecialistAgent } from "../../services/agentApi";
import { useRepo } from "../../store/RepoContext";
import styles from "./AgentsPage.module.css";

const SOURCE_LABELS = {
  rag: "Extrait RAG",
  symbol_search: "Symbole",
  graph_callers: "Appelant",
  graph_callees: "Appelé",
  graph_impact: "Impact",
  finding: "Finding",
  overview: "Vue d'ensemble"
};

export function AgentsPage() {
  const { activeRepo } = useRepo();
  const [agents, setAgents] = useState([]);
  const [selectedName, setSelectedName] = useState("researcher");
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [searchedQuestion, setSearchedQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [catalogLoading, setCatalogLoading] = useState(true);
  const [runsByAgent, setRunsByAgent] = useState({});
  const [error, setError] = useState("");

  const selectedAgent =
    agents.find((agent) => agent.name === selectedName) ?? agents[0] ?? null;

  const loadRuns = useCallback(async () => {
    try {
      const data = await getAgentRuns(200);
      const counts = Object.fromEntries(
        (data.summary?.by_agent ?? []).map((item) => [item.agent, item.total])
      );
      setRunsByAgent(counts);
    } catch {
      setRunsByAgent({});
    }
  }, []);

  useEffect(() => {
    let active = true;
    getAgentCatalog()
      .then((data) => {
        if (!active) return;
        const catalog = Array.isArray(data.agents) ? data.agents : [];
        setAgents(catalog);
        if (catalog.length > 0) {
          setSelectedName((current) =>
            catalog.some((agent) => agent.name === current) ? current : catalog[0].name
          );
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      })
      .finally(() => {
        if (active) setCatalogLoading(false);
      });
    loadRuns();
    return () => {
      active = false;
    };
  }, [loadRuns]);

  const selectAgent = (name) => {
    setSelectedName(name);
    setResult(null);
    setSearchedQuestion("");
    setQuestion("");
    setError("");
  };

  const run = async (value = question) => {
    const query = value.trim();
    if (!query || loading || !selectedAgent) return;

    setQuestion(query);
    setSearchedQuestion(query);
    setLoading(true);
    setError("");
    try {
      setResult(await runSpecialistAgent(activeRepo, selectedAgent.name, query, 10));
      loadRuns();
    } catch (requestError) {
      setResult(null);
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const overview = result?.overview;
  const suggestions = selectedAgent?.sample_questions ?? [];
  const selectedRuns = selectedAgent ? runsByAgent[selectedAgent.name] ?? 0 : 0;

  return (
    <div className={styles.page}>
      <Topbar
        title="Agents"
        subtitle="Huit agents spécialisés, en lecture seule, avec preuves, citations et traces d'exécution."
        breadcrumbs={<span>DevKnowledgeHub / Agents</span>}
        actions={<span className={styles.repoChip}>Dépôt : {activeRepo}</span>}
      />

      <div className={styles.content}>
        <Card
          title="Catalogue d'agents"
          subtitle={
            catalogLoading
              ? "Chargement du catalogue..."
              : `${agents.length} agents disponibles et instrumentés dans MLOps.`
          }
        >
          {agents.length > 0 ? (
            <div className={styles.agentGrid}>
              {agents.map((agent) => (
                <button
                  key={agent.name}
                  type="button"
                  className={`${styles.agentCard} ${
                    agent.name === selectedName ? styles.agentCardActive : ""
                  }`}
                  onClick={() => selectAgent(agent.name)}
                  aria-pressed={agent.name === selectedName}
                >
                  <span className={styles.agentHeading}>
                    <strong>{agent.label}</strong>
                    <span className={styles.agentCount}>
                      {runsByAgent[agent.name] ?? 0} exéc.
                    </span>
                  </span>
                  <span className={styles.agentDescription}>{agent.description}</span>
                  <span className={styles.capabilities}>
                    {agent.capabilities.map((capability) => (
                      <span key={capability} className={styles.capability}>
                        {capability}
                      </span>
                    ))}
                  </span>
                  <span className={styles.agentMeta}>
                    {agent.read_only ? "Lecture seule" : "Écriture"}
                    {agent.uses_llm ? " · LLM" : " · Sans LLM"}
                    {agent.uses_graph ? " · Graphe" : ""}
                  </span>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState
              title={catalogLoading ? "Chargement..." : "Catalogue indisponible"}
              description="Vérifie que le backend FastAPI est démarré."
            />
          )}
        </Card>

        {selectedAgent && (
          <Card
            title={selectedAgent.label}
            subtitle={selectedAgent.description}
            actions={
              <span className={styles.agentChip}>
                {selectedAgent.name} · {selectedRuns} exécution(s)
              </span>
            }
          >
            <form
              className={styles.searchForm}
              onSubmit={(event) => {
                event.preventDefault();
                run();
              }}
            >
              <label className={styles.srOnly} htmlFor="agent-question">
                Question pour l'agent sélectionné
              </label>
              <input
                id="agent-question"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder={suggestions[0] ?? "Pose une question sur le dépôt"}
                minLength={3}
                maxLength={1000}
                required
              />
              <Button
                type="submit"
                variant="primary"
                loading={loading}
                disabled={!question.trim()}
              >
                Exécuter
              </Button>
            </form>

            <div className={styles.suggestions} aria-label="Questions suggérées">
              {suggestions.map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  disabled={loading}
                  onClick={() => run(suggestion)}
                >
                  {suggestion}
                </button>
              ))}
            </div>
            <p className={styles.hint}>
              Chaque exécution est enregistrée dans MLOps avec le nom de l'agent, sa durée
              et le nombre de preuves. Aucun agent ne modifie ni n'exécute le code.
            </p>
          </Card>
        )}

        {error && (
          <Card>
            <p className={styles.error}>
              L'exécution a échoué : {error}
              {error.includes("404") || error.toLowerCase().includes("index")
                ? " Vérifie que le dépôt est importé et indexé."
                : ""}
            </p>
          </Card>
        )}

        {loading && (
          <Card>
            <p className={styles.loading}>
              L'agent consulte ses sources, vérifie ses preuves et prépare une réponse...
            </p>
          </Card>
        )}

        {result && (
          <>
            {overview && (
              <section className={styles.stats} aria-label="Statistiques du dépôt">
                <CardStat label="Fichiers" value={overview.stats?.files ?? "—"} />
                <CardStat label="Symboles" value={overview.stats?.symbols ?? "—"} />
                <CardStat label="Imports" value={overview.stats?.imports ?? "—"} />
                <CardStat label="Appels résolus" value={overview.stats?.calls ?? "—"} />
              </section>
            )}

            <Card
              title={`Réponse — ${selectedAgent?.label ?? result.agent ?? "agent"}`}
              subtitle={`Question : ${searchedQuestion}${
                result.model ? ` · Modèle : ${result.model}` : ""
              }`}
            >
              {result.answer && <div className={styles.answer}>{result.answer}</div>}

              {overview && (
                <div className={styles.overview}>
                  {overview.top_modules?.length > 0 && (
                    <section>
                      <h3>Modules</h3>
                      <ul className={styles.pillList}>
                        {overview.top_modules.map((module) => (
                          <li key={module.name}>{module.name}</li>
                        ))}
                      </ul>
                    </section>
                  )}
                  {overview.top_files?.length > 0 && (
                    <section>
                      <h3>Fichiers principaux</h3>
                      <ul className={styles.overviewFiles}>
                        {overview.top_files.map((file) => (
                          <li key={file.path}>
                            <code>{file.path}</code>
                            <span>{file.symbols} symbole(s)</span>
                          </li>
                        ))}
                      </ul>
                    </section>
                  )}
                </div>
              )}

              {result.evidence.length > 0 ? (
                <ol className={styles.evidence}>
                  {result.evidence.map((item, index) => (
                    <li key={`${item.qualified_name}-${item.file ?? ""}-${index}`}>
                      <div className={styles.evidenceHeading}>
                        {item.id && <span className={styles.sourceId}>[{item.id}]</span>}
                        <strong>{item.qualified_name}</strong>
                        <span className={styles.badge}>
                          {SOURCE_LABELS[item.source] ?? item.source}
                        </span>
                        {item.kind && <span className={styles.kind}>{item.kind}</span>}
                      </div>
                      {item.file && (
                        <p className={styles.location}>
                          <code>
                            {item.file}
                            {item.start_line ? `:${item.start_line}-${item.end_line}` : ""}
                          </code>
                          {item.source !== "rag" && item.qualified_name && (
                            <Link
                              to={`/architecture?focus=${encodeURIComponent(
                                item.qualified_name
                              )}`}
                            >
                              Voir dans le graphe
                            </Link>
                          )}
                        </p>
                      )}
                      <p className={styles.reason}>{item.reason}</p>
                      {item.snippet && <pre className={styles.snippet}>{item.snippet}</pre>}
                    </li>
                  ))}
                </ol>
              ) : (
                <EmptyState
                  title="Aucune source trouvée"
                  description="Essaie avec un nom de fonction, de classe ou un autre terme métier."
                />
              )}

              {result.terms.length > 0 && (
                <p className={styles.terms}>
                  Termes de code recherchés : {result.terms.join(", ")}
                </p>
              )}
              <details className={styles.trace}>
                <summary>
                  Trace d'exécution ({result.trace.length} étape(s)) — agent {result.agent}
                </summary>
                <ol>
                  {result.trace.map((step, index) => (
                    <li key={`${step.tool}-${index}`}>
                      <code>{step.tool}</code>
                      {step.args?.term && <> — terme « {step.args.term} »</>}
                      {step.args?.qualified_name && <> — {step.args.qualified_name}</>}
                      {step.args?.action && <> — action {step.args.action}</>}
                      {" "}— {step.n_results} résultat(s)
                    </li>
                  ))}
                </ol>
              </details>
            </Card>
          </>
        )}

        {!result && !error && !loading && selectedAgent && (
          <Card>
            <EmptyState
              title={`${selectedAgent.label} prêt`}
              description="Pose une question ou choisis une suggestion pour lancer l'agent."
            />
          </Card>
        )}
      </div>
    </div>
  );
}
