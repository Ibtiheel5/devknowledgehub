import { useEffect, useState } from "react";
import { Topbar } from "../../components/layout";
import { Button, Card, EmptyState, SearchInput } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getRagStats, searchRag } from "../../services/ragApi";
import styles from "./RagSearchPage.module.css";

const SUGGESTIONS = [
  "Où est définie la logique d'authentification ?",
  "Comment le serveur est-il configuré ?",
  "Quelles sont les classes et fonctions principales ?",
  "Comment les erreurs sont-elles gérées ?"
];

export function RagSearchPage() {
  const { activeRepo } = useRepo();
  const [question, setQuestion] = useState("");
  const [submitted, setSubmitted] = useState("");
  const [hits, setHits] = useState([]);
  const [terms, setTerms] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    setStats(null);
    getRagStats(activeRepo)
      .then((data) => {
        if (active) setStats(data);
      })
      .catch(() => {
        if (active) setStats(null);
      });
    return () => {
      active = false;
    };
  }, [activeRepo]);

  const run = async (value = question) => {
    const query = value.trim();
    if (!query || loading) return;

    setQuestion(query);
    setSubmitted(query);
    setLoading(true);
    setError("");
    try {
      const result = await searchRag(activeRepo, query, 8);
      setHits(Array.isArray(result.hits) ? result.hits : []);
      setTerms(Array.isArray(result.terms) ? result.terms : []);
    } catch (requestError) {
      setHits([]);
      setTerms([]);
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  };

  const indexedLabel = stats
    ? `${stats.chunks} extraits · ${stats.files} fichiers indexés`
    : "Dépôt non indexé ou index indisponible";

  return (
    <div className={styles.page}>
      <Topbar
        title="Recherche RAG"
        subtitle="Recherche sémantique sur le code et la documentation indexés, avec score et extraits."
        breadcrumbs={<span>DevKnowledgeHub / Recherche RAG</span>}
        actions={<span className={styles.repoChip}>Dépôt : {activeRepo}</span>}
      />

      <div className={styles.content}>
        <Card
          title="Interroger l'index"
          subtitle={`${indexedLabel} — projet actif : ${activeRepo}`}
        >
          <form
            className={styles.searchForm}
            onSubmit={(event) => {
              event.preventDefault();
              run();
            }}
          >
            <label className={styles.srOnly} htmlFor="rag-question">
              Question de recherche
            </label>
            <SearchInput
              id="rag-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ex. où est gérée l'authentification ?"
              minLength={3}
              maxLength={500}
              required
            />
            <Button
              type="submit"
              variant="primary"
              loading={loading}
              disabled={!question.trim()}
            >
              Rechercher
            </Button>
          </form>

          <div className={styles.suggestions} aria-label="Recherches suggérées">
            {SUGGESTIONS.map((suggestion) => (
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
            La recherche combine la similarité vectorielle et un bonus lexical sur les
            noms de symboles. Les scores sont normalisés entre 0 et 1.
          </p>
        </Card>

        {error && (
          <Card>
            <p className={styles.error}>La recherche a échoué : {error}</p>
          </Card>
        )}

        {loading && (
          <Card>
            <p className={styles.loading}>Recherche des extraits les plus proches...</p>
          </Card>
        )}

        {!loading && submitted && !error && (
          <Card
            title={`${hits.length} résultat(s)`}
            subtitle={
              terms.length > 0
                ? `Question : ${submitted} · termes de code : ${terms.join(", ")}`
                : `Question : ${submitted}`
            }
          >
            {hits.length > 0 ? (
              <ol className={styles.hits}>
                {hits.map((hit, index) => (
                  <li
                    key={`${hit.file}-${hit.symbol || ""}-${hit.start_line}-${index}`}
                    className={styles.hit}
                  >
                    <div className={styles.hitHead}>
                      <strong>{hit.symbol || hit.file}</strong>
                      <span className={styles.score}>
                        score {Math.round((hit.score ?? 0) * 100)}%
                      </span>
                      {hit.kind && <span className={styles.badge}>{hit.kind}</span>}
                    </div>
                    <p className={styles.meta}>
                      <code>
                        {hit.file}
                        {hit.start_line ? `:${hit.start_line}-${hit.end_line}` : ""}
                      </code>
                      {typeof hit.vector_score === "number" && (
                        <span>similarité vectorielle : {hit.vector_score.toFixed(3)}</span>
                      )}
                    </p>
                    <pre className={styles.snippet}>{hit.snippet}</pre>
                  </li>
                ))}
              </ol>
            ) : (
              <EmptyState
                title="Aucun extrait trouvé"
                description="Essaie un nom de fonction, de classe ou de fichier. Si le dépôt n'est pas indexé, importe-le depuis la page Dépôts."
              />
            )}
          </Card>
        )}

        {!submitted && !loading && (
          <Card>
            <EmptyState
              title="Recherche prête"
              description="Pose une question ou choisis une suggestion pour interroger l'index vectoriel du dépôt actif."
            />
          </Card>
        )}
      </div>
    </div>
  );
}
