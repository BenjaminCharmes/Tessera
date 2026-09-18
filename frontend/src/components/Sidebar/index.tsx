import { useState } from "react";
import ProjectHeader from "./ProjectHeader";
import FileTree from "../FileTree";
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
  onShowDiff?: (ticketId: string) => void;
  selection?: string[];
  onToggleQueue?: (ticketId: string) => void;
  onRunQueue?: () => void;
  onRunAutonome?: (options: { depuisGithub: boolean }) => void;
  onClearQueue?: () => void;
  queueEnCours?: boolean;
  onToggleKanban: () => void;
  onTicketCreated?: (ticket: Ticket) => void;
  onBatchCreated?: (tickets: Ticket[]) => void;
  onSelectTicketById?: (ticketId: string) => void;
  onAgentCreated?: (role: string) => void;
  agentSelectionne?: string | null;
  onSelectAgent?: (role: string) => void;
  openFilePath?: string | null;
  onOpenFile?: (path: string) => void;
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
  onShowDiff,
  selection,
  onToggleQueue,
  onRunQueue,
  onRunAutonome,
  onClearQueue,
  queueEnCours,
  onToggleKanban,
  onTicketCreated,
  onBatchCreated,
  onSelectTicketById,
  onAgentCreated,
  agentSelectionne,
  onSelectAgent,
  openFilePath,
  onOpenFile,
}: SidebarProps) {
  // L'état git est replié par défaut : il occupe de la place, et on ne le
  // consulte qu'au moment de lier un dépôt ou de retirer le projet. Ce qui
  // compte, c'est qu'il soit à un clic et non à un écran de défilement.
  const [gitOuvert, setGitOuvert] = useState(false);

  return (
    <div className="flex h-full flex-col bg-zinc-900 text-sm text-zinc-200">
      <ProjectHeader
        project={activeProject}
        gitOuvert={gitOuvert}
        onBasculerGit={() => setGitOuvert((v) => !v)}
      />

      {gitOuvert && activeProject && (
        <div className="max-h-64 overflow-y-auto overflow-x-hidden border-b border-zinc-800">
          <GitLinkPanel project={activeProject} />
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
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
          onShowDiff={onShowDiff}
          selection={selection}
          onToggleQueue={onToggleQueue}
          onRunQueue={onRunQueue}
          onRunAutonome={onRunAutonome}
          onClearQueue={onClearQueue}
          queueEnCours={queueEnCours}
          onToggleKanban={onToggleKanban}
          onTicketCreated={onTicketCreated}
          onBatchCreated={onBatchCreated}
        />
      )}
      {panel === "files" &&
        (activeProject ? (
          <FileTree
            racine={activeProject.path}
            fichierActif={openFilePath ?? null}
            onSelectFile={onOpenFile ?? (() => {})}
          />
        ) : (
          <p className="px-3 py-3 text-xs text-zinc-500">
            Sélectionne un projet pour parcourir ses fichiers.
          </p>
        ))}
      {panel === "history" && (
        <RunHistory
          runs={runs}
          loading={runsLoading}
          error={runsError}
          onSelectTicket={onSelectTicketById}
        />
      )}
      {panel === "agents" && (
        <AgentList
          onAgentCreated={onAgentCreated ?? (() => {})}
          onSelect={onSelectAgent}
          selectionne={agentSelectionne ?? null}
        />
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
    </div>
  );
}
