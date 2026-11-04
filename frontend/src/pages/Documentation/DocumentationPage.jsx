import { useCallback, useEffect, useMemo, useState } from "react";
import { Topbar } from "../../components/layout";
import {
  Card,
  EmptyState,
  SearchInput,
  StatusPill
} from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { getProjectDocument, getProjectDocuments } from "../../services/projectApi";
import styles from "../page.module.css";

export function DocumentationPage() {
  const { activeRepo } = useRepo();
  const [documents, setDocuments] = useState([]);
  const [selected, setSelected] = useState(null);
  const [content, setContent] = useState(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadingDocument, setLoadingDocument] = useState(false);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getProjectDocuments(activeRepo);
      const items = Array.isArray(result.documents) ? result.documents : [];
      setDocuments(items);
      if (items.length > 0) {
        setSelected((current) =>
          items.some((item) => item.path === current?.path) ? current : items[0]
        );
      } else {
        setSelected(null);
        setContent(null);
      }
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!selected) return;
    let cancelled = false;
    setLoadingDocument(true);
    getProjectDocument(activeRepo, selected.path)
      .then((document) => {
        if (!cancelled) setContent(document);
      })
      .catch((err) => {
        if (!cancelled) setError(err);
      })
      .finally(() => {
        if (!cancelled) setLoadingDocument(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeRepo, selected]);

  const filtered = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return documents;
    return documents.filter((document) =>
      [document.path, document.title, document.kind]
        .filter(Boolean)
        .join(" ")
        .toLowerCase()
        .includes(query)
    );
  }, [documents, search]);

  return (
    <div className={styles.page}>
      <Topbar
        title="Documentation"
        subtitle="Documentation indexée du dépôt actif (README, guides, ADR)."
        breadcrumbs={<span>DevKnowledgeHub / Documentation</span>}
        onRefresh={load}
        refreshing={loading}
      />
      <div className={styles.content}>
        {error && <Card><p className={styles.error}>Impossible de charger la documentation : {error.message}</p></Card>}

        <Card
          title="Documents"
          subtitle={`${documents.length} document(s) indexé(s) pour ${activeRepo}`}
          headerAction={
            <SearchInput
              placeholder="Rechercher un document..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          }
        >
          {filtered.length === 0 ? (
            <EmptyState
              title={loading ? "Chargement…" : "Aucun document"}
              description={
                loading
                  ? "Récupération de l'index documentaire."
                  : "Lancez une ingestion du projet pour indexer README et documentation."
              }
            />
          ) : (
            <div className={styles.split}>
              <div className={styles.list}>
                {filtered.map((document) => (
                  <button
                    key={document.path}
                    type="button"
                    className={`${styles.listButton} ${
                      selected?.path === document.path ? styles.active : ""
                    }`}
                    onClick={() => setSelected(document)}
                  >
                    <strong>{document.title || document.path.split("/").pop()}</strong>
                    <span>{document.path}</span>
                  </button>
                ))}
              </div>

              <div>
                {selected ? (
                  <>
                    <div className={styles.row}>
                      <StatusPill status="ok" label={selected.kind ?? "document"} />
                      <span className={styles.muted}>{selected.path}</span>
                    </div>
                    {loadingDocument ? (
                      <p className={styles.muted}>Chargement du document…</p>
                    ) : (
                      <pre className={styles.preview}>
                        {content?.content ?? "Document vide."}
                      </pre>
                    )}
                  </>
                ) : (
                  <EmptyState title="Sélectionnez un document" />
                )}
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
