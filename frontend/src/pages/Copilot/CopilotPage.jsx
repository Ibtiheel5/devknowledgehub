import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { Topbar } from "../../components/layout";
import { Button, Card } from "../../components/ui";
import { useRepo } from "../../store/RepoContext";
import { askAgent } from "../../services/agentApi";
import styles from "./CopilotPage.module.css";

const SUGGESTIONS = [
  "Que fait ce projet ?",
  "Où est défini AuthService ?",
  "Qui appelle la fonction login ?",
  "Quels symboles touchent au token ?"
];

// Conserve la conversation quand on navigue entre les pages (par projet).
const chatCache = new Map();

export function CopilotPage() {
  const { activeRepo } = useRepo();
  const [messages, setMessages] = useState(() => chatCache.get(activeRepo) ?? []);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef(null);

  useEffect(() => {
    setMessages(chatCache.get(activeRepo) ?? []);
  }, [activeRepo]);

  useEffect(() => {
    chatCache.set(activeRepo, messages);
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, activeRepo]);

  const ask = async (question) => {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    setMessages((m) => [...m, { role: "user", text: q }]);
    try {
      const res = await askAgent(activeRepo, q, 8);
      setMessages((m) => [...m, { role: "agent", result: res }]);
    } catch (err) {
      setMessages((m) => [...m, { role: "agent", error: err.message }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className={styles.page}>
      <Topbar
        title="Copilot"
        subtitle="Posez une question sur le code : l'agent combine le graphe, le RAG et Ollama avec des sources."
        breadcrumbs={<span>DevKnowledgeHub / Copilot</span>}
        actions={<span className={styles.repoChip}>Projet : {activeRepo}</span>}
      />
      <div className={styles.content}>
        <Card className={styles.chatCard}>
          <div className={styles.messages}>
            {messages.length === 0 && (
              <div className={styles.welcome}>
                <p>
                  Je suis l'assistant de code de <strong>{activeRepo}</strong>. Je cherche dans les
                  extraits indexés et le graphe, puis je réponds avec des sources.
                </p>
                <div className={styles.chips}>
                  {SUGGESTIONS.map((s) => (
                    <button key={s} type="button" onClick={() => ask(s)}>{s}</button>
                  ))}
                </div>
                <p className={styles.hint}>
                  Astuce : cite des noms de code (<code>AuthService</code>, <code>refresh_token</code>).
                  Pas encore de projet ? <Link to="/repositories">Importe-le d'abord</Link>.
                </p>
              </div>
            )}

            {messages.map((m, i) =>
              m.role === "user" ? (
                <div key={i} className={`${styles.msg} ${styles.user}`}>{m.text}</div>
              ) : (
                <div key={i} className={`${styles.msg} ${styles.agent}`}>
                  <AgentAnswer message={m} />
                </div>
              )
            )}
            {busy && <div className={`${styles.msg} ${styles.agent}`}>Recherche et génération de la réponse...</div>}
            <div ref={endRef} />
          </div>

          <form
            className={styles.composer}
            onSubmit={(e) => {
              e.preventDefault();
              ask(input);
            }}
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pose ta question sur le code..."
              aria-label="Question"
            />
            <Button type="submit" variant="primary" loading={busy} disabled={!input.trim()}>
              Envoyer
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}

function AgentAnswer({ message }) {
  if (message.error) {
    return <p className={styles.error}>{message.error}</p>;
  }
  const { answer, citations, trace, model } = message.result;

  return (
    <>
      <div className={styles.answer}>{renderAnswer(answer)}</div>
      {model && <span className={styles.model}>Réponse générée par {model}</span>}
      {citations.length > 0 && (
        <div className={styles.sources}>
          <p className={styles.sectionLabel}>Références détaillées</p>
          <ul className={styles.evidence}>
            {citations.map((source) => (
              <li key={source.id}>
                <div className={styles.evHead}>
                  <strong>[{source.id}]</strong>
                  {source.symbol && <span className={styles.badge}>{source.symbol}</span>}
                  <span className={styles.badge}>{source.source === "code" ? "code" : "graphe"}</span>
                </div>
                <div className={styles.evMeta}>
                  {source.file && (
                    <code>
                      {source.file}
                      {source.start_line ? `:${source.start_line}-${source.end_line}` : ""}
                    </code>
                  )}
                  {source.source === "graph" && source.symbol && (
                    <Link
                      className={styles.evLink}
                      to={`/knowledge-graph?focus=${encodeURIComponent(source.symbol)}`}
                    >
                      Voir dans le graphe →
                    </Link>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
      <details className={styles.trace}>
        <summary>Étapes de l'agent ({trace.length})</summary>
        <ul>
          {trace.map((t, i) => (
            <li key={i}>
              <code>{t.tool}({Object.values(t.args).join(", ")})</code> → {t.n_results} résultat(s)
            </li>
          ))}
        </ul>
      </details>
    </>
  );
}

function renderAnswer(answer) {
  const lines = answer.split(/\r?\n/);
  const blocks = [];
  let paragraph = [];
  let listItems = [];
  let listType = null;

  const flushParagraph = () => {
    if (!paragraph.length) return;
    blocks.push(
      <p key={`p-${blocks.length}`}>{renderInline(paragraph.join(" "))}</p>
    );
    paragraph = [];
  };

  const flushList = () => {
    if (!listItems.length) return;
    const List = listType === "ordered" ? "ol" : "ul";
    blocks.push(
      <List key={`list-${blocks.length}`}>
        {listItems.map((item, index) => (
          <li key={index}>{renderInline(item)}</li>
        ))}
      </List>
    );
    listItems = [];
    listType = null;
  };

  lines.forEach((line) => {
    const heading = line.match(/^#{1,3}\s+(.+)$/);
    const listItem = line.match(/^\s*(?:[-*]\s+|\d+[.)]\s+)(.+)$/);

    if (heading) {
      flushParagraph();
      flushList();
      blocks.push(
        <h3 key={`h-${blocks.length}`}>{renderInline(heading[1])}</h3>
      );
    } else if (listItem) {
      flushParagraph();
      const nextListType = /^\s*\d+[.)]\s+/.test(line) ? "ordered" : "unordered";
      if (listType && listType !== nextListType) flushList();
      listType = nextListType;
      listItems.push(listItem[1]);
    } else if (!line.trim()) {
      flushParagraph();
      flushList();
    } else {
      flushList();
      paragraph.push(line.trim());
    }
  });

  flushParagraph();
  flushList();
  return blocks;
}

function renderInline(text) {
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\[S\d+\])/g;
  const parts = [];
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(<strong key={`strong-${match.index}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("`")) {
      parts.push(<code key={`code-${match.index}`}>{token.slice(1, -1)}</code>);
    } else {
      parts.push(
        <span className={styles.inlineCitation} key={`cite-${match.index}`}>
          {token}
        </span>
      );
    }
    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) parts.push(text.slice(lastIndex));
  return parts;
}
