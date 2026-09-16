import ProjectNav from "./ProjectNav";
import TicketList from "./TicketList";
import GitLinkPanel from "./GitLinkPanel";
import RunHistory from "./RunHistory";
import AgentList from "./AgentList";
import UsageDashboard from "./UsageDashboard";
import type {
  PipelineRun,
  Project,
  ProjectUsage,
  Ticket,
  TicketStatus,
} from "../../types/api";

export type { SidebarPanel } from "./panels";
import type { SidebarPanel } from "./panels";

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
  usage: ProjectUsage | null;
  usageLoading: boolean;
  usageError: string | null;
  onRefreshUsage: () => void;
  running: Set<string>;
  runningRound?: number;
  showKanban: boolean;
  onSelectProject: (project: Project) => void;
  onProjectCreated?: (project: Project) => void;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onToggleKanban: () => void;
  onTicketCreated?: (ticket: Ticket) => void;
  onBatchCreated?: (tickets: Ticket[]) => void;
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
  usage,
  usageLoading,
  usageError,
  onRefreshUsage,
  running,
  runningRound,
  showKanban,
  onSelectProject,
  onProjectCreated,
  onSelectTicket,
  onRunPipeline,
  onToggleKanban,
  onTicketCreated,
  onBatchCreated,
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
          onBatchCreated={onBatchCreated}
        />
      )}
      {/* L'état git se lit sous la liste des tickets : c'est là qu'on décide
          de lancer un pipeline, et c'est là que savoir si le projet est
          versionné a le plus de valeur (ticket-061). */}
      {panel === "tickets" && <GitLinkPanel project={activeProject} />}
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
      {panel === "usage" && (
        <UsageDashboard
          usage={usage}
          loading={usageLoading}
          error={usageError}
          onRefresh={onRefreshUsage}
        />
      )}
    </div>
  );
}
