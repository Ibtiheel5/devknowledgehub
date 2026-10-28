import { Topbar } from "../../components/layout";
import { Card, EmptyState } from "../../components/ui";
import styles from "./PlaceholderPage.module.css";

export function CodeIntelligencePage() {
  return (
    <div className={styles.page}>
      <Topbar
        title="Code Intelligence"
        subtitle="Symboles, définitions, références, héritage et qualité du code."
        breadcrumbs={<span>DevKnowledgeHub / Code Intelligence</span>}
      />
      <div className={styles.content}>
        <Card>
          <EmptyState
            title="À venir"
            description="Cette page affichera l'exploration fine du code (symboles, usages, dependents)."
          />
        </Card>
      </div>
    </div>
  );
}
