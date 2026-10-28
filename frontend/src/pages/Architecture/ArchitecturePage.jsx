import { Topbar } from "../../components/layout";
import { Card, EmptyState } from "../../components/ui";
import styles from "./PlaceholderPage.module.css";

export function ArchitecturePage() {
  return (
    <div className={styles.page}>
      <Topbar
        title="Architecture"
        subtitle="Documentation architecturale et décisions (ADR)."
        breadcrumbs={<span>DevKnowledgeHub / Architecture</span>}
      />
      <div className={styles.content}>
        <Card>
          <EmptyState
            title="À venir"
            description="Centralisera les ADR et les diagrammes du projet."
          />
        </Card>
      </div>
    </div>
  );
}
