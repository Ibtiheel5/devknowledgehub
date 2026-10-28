import { useState } from "react";
import { Link } from "react-router-dom";
import { Topbar } from "../../components/layout";
import { Button, Card, CardStat, EmptyState } from "../../components/ui";
import { searchAgent } from "../../services/agentApi";
import { useRepo } from "../../store/RepoContext";
import styles from "./AgentsPage.module.css";

const SUGGESTIONS = [
  "Où sont gérés les jetons d'authentification ?",
  "Quels fichiers configurent la base de données ?",
  "Que fait ce projet ?"
];

const SOURCE_LABELS = {
  rag: "Extrait RAG",
  symbol_search: "Symbole",
  graph_callers: "Appelant",
  graph_callees: "Appelé",
  overview: "Vue d'ensemble"
};

export function AgentsPage() {
  const { activeRepo } = useRepo();
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [searchedQuestion, setSearchedQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const search = async (value = question) => {
    const query = value.trim();
    if (!query || loading) return;

    setQuestion(query);
    setSearchedQuestion(query);
    setLoading(true);
    setError("");
    try {
      setResult(await searchAgent(activeRepo, query, 10));
    } catch (requestError) {
      setResult(null);
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const overview = result?.overview;

  return (
    <div className={styles.page}>
      <Topbar
        title="Agents"
        subtitle="Un agent planifie ses recherches, explore le code et explique ses résultats avec des sources."
        breadcrumbs={<span>DevKnowledgeHub / Agents</span>}
        actions={<span className={styles.repoChip}>Dépôt : {activeRepo}</span>}
      />

      <div className={styles.content}>
        <Card
          title="Search Agent"
          subtitle="Agent en lecture seule : il combine le RAG et le graphe, choisit des recherches complémentaires, puis synthétise une réponse citée."
        >
          <form
            className={styles.searchForm}
            onSubmit={(event) => {
              event.preventDefault();
              search();
            }}
          >
            <label className={styles.srOnly} htmlFor="agent-question">
              Question à rechercher dans le dépôt
            </label>
            <input
              id="agent-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ex. Où est définie la logique d'authentification ?"
              minLength={3}
              maxLength={1000}
              required
            />
            <Button type="submit" variant="primary" loading={loading} disabled={!question.trim()}>
              Rechercher
            </Button>
          </form>

          <div className={styles.suggestions} aria-label="Questions suggérées">
            {SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={loading}
                onClick={() => search(suggestion)}
              >
                {suggestion}
              </button>
            ))}
          </div>
          <p className={styles.hint}>
            Le dépôt doit être importé et indexé. Les réponses affichent les sources et les étapes
            de recherche pour faciliter leur vérification.
          </p>
        </Card>

        {error && (
          <Card>
            <p className={styles.error}>
              La recherche a échoué : {error}
              {error.includes("404") || error.toLowerCase().includes("index")
                ? " Vérifie que le dépôt est importé et indexé."
                : ""}
            </p>
          </Card>
        )}

        {loading && (
          <Card>
            <p className={styles.loading}>
              L’agent analyse la question, consulte les sources et prépare une réponse…
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
              title="Réponse de l’agent"
              subtitle={`Question : ${searchedQuestion}${result.model ? ` · Modèle : ${result.model}` : ""}`}
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
                              to={`/knowledge-graph?focus=${encodeURIComponent(item.qualified_name)}`}
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
                <summary>Étapes de recherche ({result.trace.length})</summary>
                <ol>
                  {result.trace.map((step, index) => (
                    <li key={`${step.tool}-${index}`}>
                      <code>{step.tool}</code>
                      {step.args?.term && <> — terme « {step.args.term} »</>}
                      {step.args?.qualified_name && <> — {step.args.qualified_name}</>}
                      {" "}· {step.n_results} résultat(s)
                    </li>
                  ))}
                </ol>
              </details>
            </Card>
          </>
        )}

        {!result && !error && !loading && (
          <Card>
            <EmptyState
              title="Search Agent prêt"
              description="Pose une question pour retrouver des extraits de code, des documents et les symboles associés dans le dépôt actif."
            />
          </Card>
        )}
      </div>
    </div>
  );
}
