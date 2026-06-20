import ProjectNav from "./ProjectNav";
import TicketList from "./TicketList";
import type { Project, Ticket, TicketStatus } from "../../types/api";

type SidebarPanel = "projects" | "tickets";

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
  running: Set<string>;
  showKanban: boolean;
  onSelectProject: (project: Project) => void;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onToggleKanban: () => void;
  onTicketCreated?: (ticket: Ticket) => void;
}

export default function Sidebar({
  panel,
  activeProject,
  activeTicket,
  byStatus,
  ticketsLoading,
  ticketsError,
  running,
  showKanban,
  onSelectProject,
  onSelectTicket,
  onRunPipeline,
  onToggleKanban,
  onTicketCreated,
}: SidebarProps) {
  return (
    <div className="h-full overflow-y-auto bg-zinc-900 text-zinc-200 text-sm">
      {panel === "projects" && (
        <ProjectNav
          activeProject={activeProject}
          onSelectProject={onSelectProject}
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
          showKanban={showKanban}
          onSelectTicket={onSelectTicket}
          onRunPipeline={onRunPipeline}
          onToggleKanban={onToggleKanban}
          onTicketCreated={onTicketCreated}
        />
      )}
    </div>
  );
}
