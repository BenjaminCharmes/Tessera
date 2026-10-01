import type { useSupervision } from "../hooks/useSupervision";
import type { useRunActif } from "../hooks/useRunActif";
import type { SidebarPanel } from "./Sidebar/panels";
import type {
  Project,
  ServiceActif,
  StatsPeriod,
  Ticket,
  TicketStatus,
  TicketUnreadable,
} from "../types/api";
import type { VueCentre } from "../vueDuCentre";
import DiffView from "./DiffView";
import AgentDetail from "./AgentDetail";
import StatsView from "./StatsView";
import SupervisionView from "./SupervisionView";
import RunView from "./RunView";
import Editor from "./Editor";
import KanbanView from "./KanbanView";
import ChatPanel from "./ChatPanel";

/**
 * La vue centrale du cockpit — ticket-252.
 *
 * Le `switch` vivait dans le JSX d'App.tsx, au milieu de la grille : le
 * composant qui décide *quoi* montrer au centre est maintenant nommé, et
 * App.tsx ne garde que la composition des régions.
 */
interface CenterViewProps {
  panel: SidebarPanel;
  vueCentre: VueCentre;
  project: Project | null;
  projets: Project[];
  ticket: Ticket | null;
  conversationId: string;
  supervision: ReturnType<typeof useSupervision>;
  servicesDuProjet: ServiceActif[];
  agentSelectionne: string | null;
  stream: ReturnType<typeof useRunActif>;
  byStatus: Record<TicketStatus, Ticket[]>;
  running: Set<string>;
  unreadable: TicketUnreadable[];
  openFilePath: string | null;
  /** Nombre de jours de la période stats, géré par useCockpit (ticket-253). */
  statsDays: StatsPeriod;
  /** Projet cible des stats — null si portée "tous projets" (ticket-253). */
  statsProjectId: string | null;
  onSelectTicket: (t: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onChangeStatus: (ticketId: string, status: TicketStatus) => void;
  /** Identifiants en file — partagé avec la sidebar (ticket-284). */
  selection?: string[];
  /** Bascule l'appartenance d'un ticket à la file (ticket-284). */
  onToggleQueue?: (ticketId: string) => void;
  /** Lance la file (ticket-284). */
  onRunQueue?: () => void;
  /** Vide la file (ticket-284). */
  onClearQueue?: () => void;
  /** Un run de file est en cours (ticket-284). */
  queueEnCours?: boolean;
}

export default function CenterView({
  panel,
  vueCentre,
  project,
  projets,
  ticket,
  conversationId,
  supervision,
  servicesDuProjet,
  agentSelectionne,
  stream,
  byStatus,
  running,
  unreadable,
  openFilePath,
  statsDays,
  statsProjectId,
  onSelectTicket,
  onRunPipeline,
  onChangeStatus,
  selection,
  onToggleQueue,
  onRunQueue,
  onClearQueue,
  queueEnCours,
}: CenterViewProps) {
  /* L'onglet Agents donne un détail au centre : le rail dit *quel* agent, le
     centre montre *ce qu'il est* (ticket-076). Pendant un run, le centre
     montre le run — sauf fichier ou diff ouvert explicitement, qui garde la
     priorité (ticket-075, ticket-178). */
  if (panel === "chat") {
    // Le chat a sa propre vue centrale (ticket-223) ; sa liste de
    // conversations vit dans la colonne 2 (ticket-250).
    return <ChatPanel project={project} conversationId={conversationId} />;
  }
  if (panel === "supervision") {
    // Vue globale : elle ne dépend d'aucun projet actif, comme les coûts.
    return (
      <SupervisionView
        supervision={supervision}
        projects={projets}
        services={servicesDuProjet}
      />
    );
  }
  if (panel === "agents") {
    return <AgentDetail role={agentSelectionne} projectId={project?.id ?? null} />;
  }
  if (panel === "usage") {
    // La période et la portée viennent de la colonne latérale (ticket-253).
    return <StatsView projectId={statsProjectId} days={statsDays} />;
  }
  if (vueCentre === "run") {
    return <RunView stream={stream} />;
  }
  if (vueCentre === "diff" && project && ticket) {
    return <DiffView projectId={project.id} ticketId={ticket.id} />;
  }
  if (vueCentre === "kanban") {
    return (
      <KanbanView
        byStatus={byStatus}
        activeTicket={ticket}
        running={running}
        githubRemote={project?.github_remote ?? null}
        projectId={project?.id ?? null}
        unreadable={unreadable}
        onSelectTicket={onSelectTicket}
        onRunPipeline={onRunPipeline}
        onChangeStatus={onChangeStatus}
        selection={selection}
        onToggleQueue={onToggleQueue}
        onRunQueue={onRunQueue}
        onClearQueue={onClearQueue}
        queueEnCours={queueEnCours}
      />
    );
  }
  return <Editor ticket={ticket} openFilePath={openFilePath} />;
}
