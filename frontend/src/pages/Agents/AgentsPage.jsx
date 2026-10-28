import { Topbar } from "../../components/layout";
import { Card, EmptyState } from "../../components/ui";
import styles from "./PlaceholderPage.module.css";

export function AgentsPage() {
  return (
    <div className={styles.page}>
      <Topbar
        title="Agents"
        subtitle="Orchestration des agents d'analyse et d'automatisation."
        breadcrumbs={<span>DevKnowledgeHub / Agents</span>}
      />
      <div className={styles.content}>
        <Card>
          <EmptyState
            title="À venir"
            description="Affichera l'état et les exécutions des agents backend."
          />
        </Card>
      </div>
    </div>
  );
}
