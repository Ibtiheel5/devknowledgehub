import { Routes, Route, Navigate } from "react-router-dom";
import { AppLayout } from "./components/layout";
import { DashboardPage } from "./pages/Dashboard/DashboardPage";
import { ProjectsPage } from "./pages/Projects/ProjectsPage";
import { ProjectOverviewPage } from "./pages/Projects/ProjectOverviewPage";
import { KnowledgeGraphPage } from "./pages/KnowledgeGraph/KnowledgeGraphPage";
import { CodeIntelligencePage } from "./pages/CodeIntelligence/CodeIntelligencePage";
import { RagSearchPage } from "./pages/RagSearch/RagSearchPage";
import { CopilotPage } from "./pages/Copilot/CopilotPage";
import { AgentsPage } from "./pages/Agents/AgentsPage";
import { TicketsPage } from "./pages/Tickets/TicketsPage";
import { DocumentationPage } from "./pages/Documentation/DocumentationPage";
import { IncidentsPage } from "./pages/Incidents/IncidentsPage";
import { ModelsPage } from "./pages/Models/ModelsPage";
import { MonitoringPage } from "./pages/Monitoring/MonitoringPage";
import { ReportsPage } from "./pages/Reports/ReportsPage";
import { SettingsPage } from "./pages/Settings/SettingsPage";
import "./styles/tokens.css";
import "./styles/global.css";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />

        <Route path="/projects" element={<ProjectsPage />} />
        <Route path="/project/overview" element={<ProjectOverviewPage />} />

        <Route path="/architecture" element={<KnowledgeGraphPage />} />
        <Route path="/code-analysis" element={<CodeIntelligencePage />} />
        <Route path="/issues" element={<TicketsPage />} />
        <Route path="/assistant" element={<CopilotPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/monitoring" element={<MonitoringPage />} />
        <Route path="/reports" element={<ReportsPage />} />
        <Route path="/settings" element={<SettingsPage />} />

        <Route path="/rag-search" element={<RagSearchPage />} />
        <Route path="/documentation" element={<DocumentationPage />} />
        <Route path="/agents" element={<AgentsPage />} />
        <Route path="/incidents" element={<IncidentsPage />} />

        <Route path="/repositories" element={<Navigate to="/projects" replace />} />
        <Route path="/knowledge-graph" element={<Navigate to="/architecture" replace />} />
        <Route path="/code-intelligence" element={<Navigate to="/code-analysis" replace />} />
        <Route path="/copilot" element={<Navigate to="/assistant" replace />} />
        <Route path="/tickets" element={<Navigate to="/issues" replace />} />
        <Route path="/mlops" element={<Navigate to="/monitoring" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
