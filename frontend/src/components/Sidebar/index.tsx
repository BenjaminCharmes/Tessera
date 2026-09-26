import { useState } from "react";
import ProjectHeader from "./ProjectHeader";
import type { UseServicesResult } from "../../hooks/useServices";
import type { FiltresTickets } from "../../lib/filtresTickets";
import type { ReglageDesNotifications } from "./PanneauxDuProjet";
import FileTree from "../FileTree";
import ProjectNav from "./ProjectNav";
import TicketList from "./TicketList";
import PanneauxDuProjet from "./PanneauxDuProjet";
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
  /** Les projets dont un run attend une réponse (ticket-186). */
  projetsEnAttente?: ReadonlySet<string>;
  /** Les services du projet actif, pour le bouton « Lancer » (ticket-138). */
  services?: UseServicesResult;
  /** La sortie d'un service, pour le panneau du projet (ticket-147). */
  sortieDeService?: (projectId: string, nom: string) => string[];
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
  maxRounds?: number | null;
  showKanban: boolean;
  /** Un run tourne mais le centre montre autre chose (ticket-178). */
  runCache?: boolean;
  /** Ramène la vue du run au centre. */
  onVoirLeRun?: () => void;
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
  onPrCreated?: (ticketId: string, prNumber: number) => void;
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
  /** Le réglage des notifications système (ticket-192). */
  notifications?: ReglageDesNotifications;
  filtres?: FiltresTickets;
  onChangeFiltres?: (f: FiltresTickets) => void;
  totalTickets?: number;
  agentsDesTickets?: string[];
  onSelectTicketById?: (ticketId: string) => void;
  onAgentCreated?: (role: string) => void;
  agentSelectionne?: string | null;
  onSelectAgent?: (role: string) => void;
  openFilePath?: string | null;
  onOpenFile?: (path: string) => void;
}

export default function Sidebar({
  panel,
  projetsEnAttente,
  services,
  sortieDeService,
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
  maxRounds,
  showKanban,
  runCache,
  onVoirLeRun,
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
  onPrCreated,
  onChangeStatus,
  notifications,
  filtres,
  onChangeFiltres,
  totalTickets,
  agentsDesTickets,
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
  const [servicesOuverts, setServicesOuverts] = useState(false);

  return (
    <div className="flex h-full flex-col bg-zinc-900 text-sm text-zinc-200">
      <ProjectHeader
        project={activeProject}
        gitOuvert={gitOuvert}
        onBasculerGit={() => setGitOuvert((v) => !v)}
        services={services}
        onOuvrirLesServices={() => setServicesOuverts(true)}
        onSelectProject={onSelectProject}
      />

      <PanneauxDuProjet
        project={activeProject}
        gitOuvert={gitOuvert}
        servicesOuverts={servicesOuverts}
        services={services}
        sortieDeService={sortieDeService}
        runEnCours={running.size > 0}
        notifications={notifications}
      />

      <div className="flex-1 overflow-y-auto">
        {panel === "projects" && (
          <ProjectNav
            activeProject={activeProject}
            onSelectProject={onSelectProject}
            onProjectCreated={onProjectCreated}
            enAttente={projetsEnAttente}
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
            maxRounds={maxRounds}
            showKanban={showKanban}
            runCache={runCache}
            onVoirLeRun={onVoirLeRun}
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
            onPrCreated={onPrCreated}
            onChangeStatus={onChangeStatus}
            filtres={filtres}
            onChangeFiltres={onChangeFiltres}
            totalTickets={totalTickets}
            agents={agentsDesTickets}
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
