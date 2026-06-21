import ProjectNav from "./ProjectNav";
import TicketList from "./TicketList";
import RunHistory from "./RunHistory";
import AgentList from "./AgentList";
import type {
  PipelineRun,
  Project,
  Ticket,
  TicketStatus,
} from "../../types/api";

export type SidebarPanel = "projects" | "tickets" | "history" | "agents";

interface IconBarProps {
  activePanel: SidebarPanel;
  onChangePanel: (panel: SidebarPanel) => void;
}

export function IconBar({ activePanel, onChangePanel }: IconBarProps) {
  return (
    <div className="flex flex-col items-center gap-1 py-3 px-1 h-full bg-zinc-900">
      <button
        onClick={() => onChangePanel("projects")}
        title="Projects"
        className={`w-9 h-9 flex items-center justify-center rounded text-base transition-colors ${
          activePanel === "projects"
            ? "bg-zinc-700 text-white"
            : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
        }`}
      >
        ◈
      </button>
      <button
        onClick={() => onChangePanel("tickets")}
        title="Tickets"
        className={`w-9 h-9 flex items-center justify-center rounded text-base transition-colors ${
          activePanel === "tickets"
            ? "bg-zinc-700 text-white"
            : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
        }`}
      >
        ☰
      </button>
      <button
        onClick={() => onChangePanel("history")}
        title="Historique"
        className={`w-9 h-9 flex items-center justify-center rounded text-base transition-colors ${
          activePanel === "history"
            ? "bg-zinc-700 text-white"
            : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
        }`}
      >
        ⏱
      </button>
      <button
        onClick={() => onChangePanel("agents")}
        title="Agents"
        className={`w-9 h-9 flex items-center justify-center rounded text-base transition-colors ${
          activePanel === "agents"
            ? "bg-zinc-700 text-white"
            : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-800"
        }`}
      >
        ⚙
      </button>
    </div>
  );
}

interface SidebarProps {
  panel: SidebarPanel;
  activeProject: Project | null;
  activeTicket: Ticket | null;
  byStatus: Record<TicketStatus, Ticket[]>;
  ticketsLoading: boolean;
  ticketsError: string | null;
  runs: PipelineRun[];
  runsLoading: boolean;
  runsError: string | null;
  running: Set<string>;
  runningRound?: number;
  showKanban: boolean;
  onSelectProject: (project: Project) => void;
  onProjectCreated?: (project: Project) => void;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onToggleKanban: () => void;
  onTicketCreated?: (ticket: Ticket) => void;
  onSelectTicketById?: (ticketId: string) => void;
  onAgentCreated?: (role: string) => void;
}

export default function Sidebar({
  panel,
  activeProject,
  activeTicket,
  byStatus,
  ticketsLoading,
  ticketsError,
  runs,
  runsLoading,
  runsError,
  running,
  runningRound,
  showKanban,
  onSelectProject,
  onProjectCreated,
  onSelectTicket,
  onRunPipeline,
  onToggleKanban,
  onTicketCreated,
  onSelectTicketById,
  onAgentCreated,
}: SidebarProps) {
  return (
    <div className="h-full overflow-y-auto bg-zinc-900 text-zinc-200 text-sm">
      {panel === "projects" && (
        <ProjectNav
          activeProject={activeProject}
          onSelectProject={onSelectProject}
          onProjectCreated={onProjectCreated}
        />
      )}
      {panel === "tickets" && (
        <TicketList
          project={activeProject}
          byStatus={byStatus}
          loading={ticketsLoading}
          error={ticketsError}
          activeTicket={activeTicket}
          running={running}
          runningRound={runningRound}
          showKanban={showKanban}
          onSelectTicket={onSelectTicket}
          onRunPipeline={onRunPipeline}
          onToggleKanban={onToggleKanban}
          onTicketCreated={onTicketCreated}
        />
      )}
      {panel === "history" && (
        <RunHistory
          runs={runs}
          loading={runsLoading}
          error={runsError}
          onSelectTicket={onSelectTicketById}
        />
      )}
      {panel === "agents" && (
        <AgentList onAgentCreated={onAgentCreated ?? (() => {})} />
      )}
    </div>
  );
}
