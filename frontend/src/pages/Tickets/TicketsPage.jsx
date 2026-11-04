import { useCallback, useEffect, useMemo, useState } from "react";
import { Topbar } from "../../components/layout";
import {
  Button,
  Card,
  CardStat,
  DataTable,
  EmptyState,
  Select,
  StatusPill,
  TextField
} from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { createProjectIssue, getProjectIssues } from "../../services/projectApi";
import { formatDateTime } from "../../utils/format";
import styles from "../page.module.css";

const KINDS = [
  { value: "", label: "Classification automatique" },
  { value: "BUG", label: "Bug" },
  { value: "FEATURE", label: "Fonctionnalité" },
  { value: "TECHNICAL_DEBT", label: "Dette technique" }
];

function kindClass(kind) {
  if (kind === "BUG" || kind === "INCIDENT") return styles.badgeDanger;
  if (kind === "TECHNICAL_DEBT") return styles.badgeWarning;
  return styles.badgeInfo;
}

function kindLabel(kind) {
  return KINDS.find((item) => item.value === kind)?.label ?? kind ?? "Inconnu";
}

export function TicketsPage() {
  const { activeRepo } = useRepo();
  const [issues, setIssues] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [kind, setKind] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await getProjectIssues(activeRepo);
      setIssues(Array.isArray(result.issues) ? result.issues : []);
    } catch (err) {
      setError(err);
    } finally {
      setLoading(false);
    }
  }, [activeRepo]);

  useEffect(() => {
    load();
  }, [load]);

  const summary = useMemo(() => {
    const count = (value) => issues.filter((issue) => issue.kind === value).length;
    return {
      total: issues.length,
      bugs: count("BUG") + count("INCIDENT"),
      features: count("FEATURE"),
      debt: count("TECHNICAL_DEBT")
    };
  }, [issues]);

  const handleCreate = async (event) => {
    event.preventDefault();
    if (!title.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await createProjectIssue(activeRepo, {
        title: title.trim(),
        description: description.trim() || null,
        kind: kind || null
      });
      setTitle("");
      setDescription("");
      setKind("");
      await load();
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  const columns = [
    {
      key: "title",
      label: "Ticket",
      render: (issue) => (
        <div>
          <strong>{issue.title}</strong>
          {issue.description && (
            <p className={styles.muted}>{issue.description.slice(0, 160)}</p>
          )}
        </div>
      )
    },
    {
      key: "kind",
      label: "Type",
      render: (issue) => (
        <span className={`${styles.badge} ${kindClass(issue.kind)}`}>
          {kindLabel(issue.kind)}
        </span>
      )
    },
    {
      key: "status",
      label: "État",
      render: (issue) => (
        <StatusPill
          status={issue.status === "closed" ? "idle" : "ok"}
          label={issue.status ?? "open"}
        />
      )
    },
    {
      key: "created_at",
      label: "Créé le",
      align: "right",
      render: (issue) => (issue.created_at ? formatDateTime(new Date(issue.created_at)) : "—")
    }
  ];

  return (
    <div className={styles.page}>
      <Topbar
        title="Tickets & incidents"
        subtitle="Tickets liés au code : bugs, fonctionnalités, dette technique et incidents."
        breadcrumbs={<span>DevKnowledgeHub / Tickets & incidents</span>}
        onRefresh={load}
        refreshing={loading}
      />
      <div className={styles.content}>
        {error && <Card><p className={styles.error}>Impossible de charger les tickets : {error.message}</p></Card>}

        <section className={styles.stats}>
          <CardStat label="Tickets" value={summary.total} />
          <CardStat label="Bugs / incidents" value={summary.bugs} />
          <CardStat label="Fonctionnalités" value={summary.features} />
          <CardStat label="Dette technique" value={summary.debt} />
        </section>

        <div className={styles.grid}>
          <Card title="Nouveau ticket" subtitle={`Ajouté au projet ${activeRepo}`}>
            <form className={styles.form} onSubmit={handleCreate}>
              <TextField
                label="Titre"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Ex. Crash à la connexion"
                required
              />
              <div>
                <label className={styles.muted} htmlFor="ticket-description">Description</label>
                <textarea
                  id="ticket-description"
                  className={styles.textarea}
                  value={description}
                  onChange={(event) => setDescription(event.target.value)}
                  placeholder="Contexte, étapes de reproduction, résultat attendu..."
                />
              </div>
              <Select
                label="Type"
                value={kind}
                onChange={(event) => setKind(event.target.value)}
              >
                {KINDS.map((item) => (
                  <option key={item.value || "auto"} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </Select>
              <Button type="submit" variant="primary" loading={saving} disabled={!title.trim()}>
                Créer le ticket
              </Button>
            </form>
          </Card>

          <Card title="Répartition" subtitle="Tickets du dépôt actif">
            <div className={styles.kv}>
              <div className={styles.kvItem}>
                <span>Total</span>
                <strong>{summary.total}</strong>
              </div>
              <div className={styles.kvItem}>
                <span>Bugs</span>
                <strong>{summary.bugs}</strong>
              </div>
              <div className={styles.kvItem}>
                <span>Fonctionnalités</span>
                <strong>{summary.features}</strong>
              </div>
              <div className={styles.kvItem}>
                <span>Dette</span>
                <strong>{summary.debt}</strong>
              </div>
            </div>
            <p className={styles.muted}>
              À l'ingestion, les tickets sont reliés aux fichiers et symboles qu'ils mentionnent
              (relations MENTIONS et AFFECTS dans le graphe).
            </p>
          </Card>
        </div>

        <Card title="Tickets du projet" subtitle={`${summary.total} ticket(s)`}>
          <DataTable
            columns={columns}
            data={issues}
            rowKey="id"
            emptyState={
              <EmptyState
                title={loading ? "Chargement…" : "Aucun ticket"}
                description={
                  loading
                    ? "Récupération des tickets."
                    : "Créez un ticket ou importez-en via l'API /issues/import."
                }
              />
            }
          />
        </Card>
      </div>
    </div>
  );
}
