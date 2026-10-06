import { lazy, Suspense } from "react";
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
import type { FiltresTickets } from "../lib/filtresTickets";
import type { VueCentre } from "../vueDuCentre";
import AgentDetail from "./AgentDetail";
import SupervisionView from "./SupervisionView";
import RunView from "./RunView";
import KanbanView from "./KanbanView";

// Vues lourdes — chargées à la demande, après le premier rendu du cockpit
// (ticket-355). DiffView et Editor tirent Monaco ; les garder lazy réduit le
// bundle initial et accélère le premier affichage.
const DiffView = lazy(() => import("./DiffView"));
const StatsView = lazy(() => import("./StatsView"));
const Editor = lazy(() => import("./Editor"));
const ChatPanel = lazy(() => import("./ChatPanel"));

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
  /** Filtres actifs sur le tableau — ticket-318. */
  filtres?: FiltresTickets;
  /** Nombre total de tickets avant filtrage — ticket-318. */
  total?: number;
  /** Nombre de tickets retenus après filtrage — ticket-318. */
  retenus?: number;
  /** Réinitialise les filtres mémorisés du projet — ticket-318. */
  onClearFiltres?: () => void;
}

function FallbackChargement() {
  return (
    <div className="flex h-full items-center justify-center text-zinc-500 text-sm">
      Chargement…
    </div>
  );
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
  filtres,
  total,
  retenus,
  onClearFiltres,
}: CenterViewProps) {
  /* L'onglet Agents donne un détail au centre : le rail dit *quel* agent, le
     centre montre *ce qu'il est* (ticket-076). Pendant un run, le centre
     montre le run — sauf fichier ou diff ouvert explicitement, qui garde la
     priorité (ticket-075, ticket-178). */
  let content: React.ReactNode;

  if (panel === "chat") {
    // Le chat a sa propre vue centrale (ticket-223) ; sa liste de
    // conversations vit dans la colonne 2 (ticket-250).
    content = <ChatPanel project={project} conversationId={conversationId} />;
  } else if (panel === "supervision") {
    // Vue globale : elle ne dépend d'aucun projet actif, comme les coûts.
    content = (
      <SupervisionView
        supervision={supervision}
        projects={projets}
        services={servicesDuProjet}
      />
    );
  } else if (panel === "agents") {
    content = <AgentDetail role={agentSelectionne} projectId={project?.id ?? null} />;
  } else if (panel === "usage") {
    // La période et la portée viennent de la colonne latérale (ticket-253).
    content = <StatsView projectId={statsProjectId} days={statsDays} />;
  } else if (vueCentre === "run") {
    content = <RunView stream={stream} />;
  } else if (vueCentre === "diff" && project && ticket) {
    content = <DiffView projectId={project.id} ticketId={ticket.id} />;
  } else if (vueCentre === "kanban") {
    content = (
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
        filtres={filtres}
        total={total}
        retenus={retenus}
        onClearFiltres={onClearFiltres}
      />
    );
  } else {
    content = (
      <Editor
        ticket={ticket}
        openFilePath={openFilePath}
        projectId={project?.id ?? null}
      />
    );
  }

  return (
    <Suspense fallback={<FallbackChargement />}>
      {content}
    </Suspense>
  );
}
