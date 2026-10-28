import { Topbar } from "../../components/layout";
import { Card, EmptyState } from "../../components/ui";
import styles from "./PlaceholderPage.module.css";

export function DocumentationPage() {
  return (
    <div className={styles.page}>
      <Topbar
        title="Documentation"
        subtitle="Vue unifiée sur la documentation projet."
        breadcrumbs={<span>DevKnowledgeHub / Documentation</span>}
      />
      <div className={styles.content}>
        <Card>
          <EmptyState
            title="À venir"
            description="Permettra de naviguer dans la documentation indexée."
          />
        </Card>
      </div>
    </div>
  );
}
