import { Topbar } from "../../components/layout";
import { Card, EmptyState } from "../../components/ui";
import styles from "./PlaceholderPage.module.css";

export function RagSearchPage() {
  return (
    <div className={styles.page}>
      <Topbar
        title="RAG Search"
        subtitle="Recherche sémantique sur le code, la documentation et les tickets."
        breadcrumbs={<span>DevKnowledgeHub / RAG Search</span>}
      />
      <div className={styles.content}>
        <Card>
          <EmptyState
            title="À venir"
            description="Connectez les endpoints RAG du backend pour activer la recherche hybride."
          />
        </Card>
      </div>
    </div>
  );
}
