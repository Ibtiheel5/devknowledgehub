import {
  Activity,
  BarChart3,
  BookOpen,
  Boxes,
  Bot,
  BrainCircuit,
  Code2,
  Cpu,
  FolderKanban,
  GitBranch,
  LayoutDashboard,
  Network,
  Search,
  Settings,
  Ticket
} from "lucide-react";

const ICONS = {
  dashboard: LayoutDashboard,
  projects: FolderKanban,
  architecture: Network,
  graph: GitBranch,
  code: Code2,
  issues: Ticket,
  assistant: Bot,
  models: BrainCircuit,
  monitoring: Activity,
  reports: BarChart3,
  settings: Settings,
  search: Search,
  documentation: BookOpen,
  book: BookOpen,
  cpu: Cpu,
  modules: Boxes,
  home: LayoutDashboard
};

export function NavIcon({ name, size = 18, ...props }) {
  const Icon = ICONS[name] || LayoutDashboard;
  return <Icon size={size} strokeWidth={1.9} aria-hidden="true" {...props} />;
}
