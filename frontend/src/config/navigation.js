export const navItems = [
  { to: "/", label: "Tableau de bord", short: "Dashboard", icon: "dashboard" },
  { to: "/projects", label: "Projets", short: "Projects", icon: "projects" },
  {
    to: "/architecture",
    label: "Architecture & graphe",
    short: "Architecture",
    icon: "architecture"
  },
  { to: "/code-analysis", label: "Analyse du code", short: "Code Analysis", icon: "code" },
  { to: "/issues", label: "Tickets & incidents", short: "Issues", icon: "issues" },
  { to: "/assistant", label: "Assistant IA", short: "AI Assistant", icon: "assistant" },
  { to: "/models", label: "Modèles ML", short: "ML Models", icon: "models" },
  { to: "/monitoring", label: "Monitoring", short: "Monitoring", icon: "monitoring" },
  { to: "/reports", label: "Rapports", short: "Reports", icon: "reports" },
  { to: "/settings", label: "Paramètres", short: "Settings", icon: "settings" }
];

export const secondaryItems = [
  { to: "/rag-search", label: "Recherche RAG", icon: "search" },
  { to: "/documentation", label: "Documentation", icon: "book" },
  { to: "/agents", label: "Agents spécialisés", icon: "cpu" }
];

export const routeTitles = {
  "/": "Tableau de bord",
  "/projects": "Projets",
  "/architecture": "Architecture & graphe",
  "/code-analysis": "Analyse du code",
  "/issues": "Tickets & incidents",
  "/assistant": "Assistant IA",
  "/models": "Modèles ML",
  "/monitoring": "Monitoring",
  "/reports": "Rapports",
  "/settings": "Paramètres",
  "/rag-search": "Recherche RAG",
  "/documentation": "Documentation",
  "/agents": "Agents spécialisés"
};
