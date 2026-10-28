import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout";
import { OverviewPage } from "./pages/Overview/OverviewPage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraph/KnowledgeGraphPage";
import { RepositoriesPage } from "./pages/Repositories/RepositoriesPage";
import { CodeIntelligencePage } from "./pages/CodeIntelligence/CodeIntelligencePage";
import { RagSearchPage } from "./pages/RagSearch/RagSearchPage";
import { CopilotPage } from "./pages/Copilot/CopilotPage";
import { AgentsPage } from "./pages/Agents/AgentsPage";
import { TicketsPage } from "./pages/Tickets/TicketsPage";
import { DocumentationPage } from "./pages/Documentation/DocumentationPage";
import { IncidentsPage } from "./pages/Incidents/IncidentsPage";
import { MLOpsPage } from "./pages/MLOps/MLOpsPage";
import { ArchitecturePage } from "./pages/Architecture/ArchitecturePage";
import "./styles/tokens.css";
import "./styles/global.css";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<OverviewPage />} />
        <Route path="/knowledge-graph" element={<KnowledgeGraphPage />} />
        <Route path="/repositories" element={<RepositoriesPage />} />
        <Route path="/code-intelligence" element={<CodeIntelligencePage />} />
        <Route path="/rag-search" element={<RagSearchPage />} />
        <Route path="/copilot" element={<CopilotPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/tickets" element={<TicketsPage />} />
        <Route path="/documentation" element={<DocumentationPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />
        <Route path="/mlops" element={<MLOpsPage />} />
        <Route path="/architecture" element={<ArchitecturePage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
