import { Topbar } from "../../components/layout";
import { Card, EmptyState } from "../../components/ui";
import styles from "./PlaceholderPage.module.css";

export function TicketsPage() {
  return (
    <div className={styles.page}>
      <Topbar
        title="Tickets"
        subtitle="Suivi des tickets liés au code et aux incidents."
        breadcrumbs={<span>DevKnowledgeHub / Tickets</span>}
      />
      <div className={styles.content}>
        <Card>
          <EmptyState
            title="À venir"
            description="À connecter lorsque des données tickets seront indexées."
          />
        </Card>
      </div>
    </div>
  );
}
