import { Topbar } from "../../components/layout";
import { Card, EmptyState } from "../../components/ui";
import styles from "./PlaceholderPage.module.css";

export function IncidentsPage() {
  return (
    <div className={styles.page}>
      <Topbar
        title="Incidents"
        subtitle="Historique et suivi des incidents."
        breadcrumbs={<span>DevKnowledgeHub / Incidents</span>}
      />
      <div className={styles.content}>
        <Card>
          <EmptyState
            title="À venir"
            description="Page dédiée au suivi incidents (SLO, alertes)."
          />
        </Card>
      </div>
    </div>
  );
}
