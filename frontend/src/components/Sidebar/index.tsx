import { useState } from "react";
import ProjectHeader from "./ProjectHeader";
import PanneauUsage from "./PanneauUsage";
import type { UseServicesResult } from "../../hooks/useServices";
import type { FiltresTickets } from "../../lib/filtresTickets";
import type { ReglageDesNotifications } from "./PanneauxDuProjet";
import FileTree from "../FileTree";
import ProjectNav from "./ProjectNav";
import TicketList from "./TicketList";
import PanneauxDuProjet from "./PanneauxDuProjet";
import RunHistory from "./RunHistory";
import AgentList from "./AgentList";
import ConversationSidebar from "../ChatPanel/ConversationSidebar";
import type {
  PipelineRun,
  Project,
  StatsPeriod,
  Ticket,
  TicketStatus,
} from "../../types/api";

export type { SidebarPanel } from "./panels";
import type { SidebarPanel } from "./panels";

/*
 * Les props sont groupées par domaine (ticket-252) : App en passait une
 * cinquantaine à plat, et plus personne ne voyait qui dépendait de quoi.
 * Chaque groupe se lit comme une phrase : « voilà ce que la colonne sait
 * des tickets », etc.
 */

export interface ProjetSidebar {
  actif: Project | null;
  /** Les projets dont un run attend une réponse (ticket-186). */
  enAttente?: ReadonlySet<string>;
  /** Les services du projet actif, pour le bouton « Lancer » (ticket-138). */
  services?: UseServicesResult;
  /** La sortie d'un service, pour le panneau du projet (ticket-147). */
  sortieDeService?: (projectId: string, nom: string) => string[];
  /** Le réglage des notifications système (ticket-192). */
  notifications?: ReglageDesNotifications;
  onSelect: (project: Project) => void;
  onCreated?: (project: Project) => void;
}

export interface TicketsSidebar {
  byStatus: Record<TicketStatus, Ticket[]>;
  loading: boolean;
  error: string | null;
  actif: Ticket | null;
  running: Set<string>;
  runningRound?: number;
  maxRounds?: number | null;
  showKanban: boolean;
  /** Un run tourne mais le centre montre autre chose (ticket-178). */
  runCache?: boolean;
  filtres?: FiltresTickets;
  total?: number;
  agents?: string[];
  selection?: string[];
  queueEnCours?: boolean;
  /** Ramène la vue du run au centre. */
  onVoirLeRun?: () => void;
  onSelect: (ticket: Ticket) => void;
  onSelectById?: (ticketId: string) => void;
  onRunPipeline: (ticketId: string) => void;
  onShowDiff?: (ticketId: string) => void;
  onToggleQueue?: (ticketId: string) => void;
  onRunQueue?: () => void;
  onRunAutonome?: (options: { depuisGithub: boolean }) => void;
  onClearQueue?: () => void;
  onToggleKanban: () => void;
  onChangeFiltres?: (f: FiltresTickets) => void;
  onCreated?: (ticket: Ticket) => void;
  onBatchCreated?: (tickets: Ticket[]) => void;
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
}

export interface RunsSidebar {
  liste: PipelineRun[];
  loading: boolean;
  error: string | null;
}

export interface UsageSidebar {
  /** Période sélectionnée dans la colonne, transmise à StatsView (ticket-253). */
  days: StatsPeriod;
  setDays: (d: StatsPeriod) => void;
  /** Portée effective : "tous" si aucun projet actif, sinon le choix utilisateur (ticket-258). */
  portee: "projet" | "tous";
  setPortee: (p: "projet" | "tous") => void;
  /** Id du projet actif — null si aucun, utilisé pour désactiver "Ce projet". */
  projetActifId: string | null;
}

export interface ChatSidebar {
  /** La conversation active — la liste vit ici (ticket-250). */
  conversationId?: string;
  onSelect?: (id: string) => void;
  onNew?: () => void;
}

export interface FichiersSidebar {
  ouvert?: string | null;
  onOpen?: (path: string) => void;
}

export interface AgentsSidebar {
  selectionne?: string | null;
  onSelect?: (role: string) => void;
  onCreated?: (role: string) => void;
}

interface SidebarProps {
  panel: SidebarPanel;
  projet: ProjetSidebar;
  tickets: TicketsSidebar;
  runs: RunsSidebar;
  usage: UsageSidebar;
  chat?: ChatSidebar;
  fichiers?: FichiersSidebar;
  agents?: AgentsSidebar;
}

export default function Sidebar({
  panel,
  projet,
  tickets,
  runs,
  usage,
  chat,
  fichiers,
  agents,
}: SidebarProps) {
  // L'état git est replié par défaut : il occupe de la place, et on ne le
  // consulte qu'au moment de lier un dépôt ou de retirer le projet. Ce qui
  // compte, c'est qu'il soit à un clic et non à un écran de défilement.
  const [gitOuvert, setGitOuvert] = useState(false);
  const [servicesOuverts, setServicesOuverts] = useState(false);

  return (
    <div className="flex h-full flex-col bg-zinc-900 text-sm text-zinc-200">
      <ProjectHeader
        project={projet.actif}
        gitOuvert={gitOuvert}
        onBasculerGit={() => setGitOuvert((v) => !v)}
        services={projet.services}
        onOuvrirLesServices={() => setServicesOuverts(true)}
        onSelectProject={projet.onSelect}
      />

      <PanneauxDuProjet
        project={projet.actif}
        gitOuvert={gitOuvert}
        servicesOuverts={servicesOuverts}
        services={projet.services}
        sortieDeService={projet.sortieDeService}
        runEnCours={tickets.running.size > 0}
        notifications={projet.notifications}
      />

      <div className="flex-1 overflow-y-auto">
        {panel === "projects" && (
          <ProjectNav
            activeProject={projet.actif}
            onSelectProject={projet.onSelect}
            onProjectCreated={projet.onCreated}
            enAttente={projet.enAttente}
          />
        )}
        {panel === "tickets" && (
          <TicketList
            project={projet.actif}
            byStatus={tickets.byStatus}
            loading={tickets.loading}
            error={tickets.error}
            activeTicket={tickets.actif}
            running={tickets.running}
            runningRound={tickets.runningRound}
            maxRounds={tickets.maxRounds}
            showKanban={tickets.showKanban}
            runCache={tickets.runCache}
            onVoirLeRun={tickets.onVoirLeRun}
            onSelectTicket={tickets.onSelect}
            onRunPipeline={tickets.onRunPipeline}
            onShowDiff={tickets.onShowDiff}
            selection={tickets.selection}
            onToggleQueue={tickets.onToggleQueue}
            onRunQueue={tickets.onRunQueue}
            onRunAutonome={tickets.onRunAutonome}
            onClearQueue={tickets.onClearQueue}
            queueEnCours={tickets.queueEnCours}
            onToggleKanban={tickets.onToggleKanban}
            onTicketCreated={tickets.onCreated}
            onBatchCreated={tickets.onBatchCreated}
            onChangeStatus={tickets.onChangeStatus}
            filtres={tickets.filtres}
            onChangeFiltres={tickets.onChangeFiltres}
            totalTickets={tickets.total}
            agents={tickets.agents}
          />
        )}
        {panel === "files" &&
          (projet.actif ? (
            <FileTree
              racine={projet.actif.path}
              fichierActif={fichiers?.ouvert ?? null}
              onSelectFile={fichiers?.onOpen ?? (() => {})}
            />
          ) : (
            <p className="px-3 py-3 text-xs text-zinc-500">
              Sélectionne un projet pour parcourir ses fichiers.
            </p>
          ))}
        {panel === "history" && (
          <RunHistory
            runs={runs.liste}
            loading={runs.loading}
            error={runs.error}
            onSelectTicket={tickets.onSelectById}
          />
        )}
        {panel === "agents" && (
          <AgentList
            onAgentCreated={agents?.onCreated ?? (() => {})}
            onSelect={agents?.onSelect}
            selectionne={agents?.selectionne ?? null}
          />
        )}
        {panel === "chat" &&
          (projet.actif ? (
            <ConversationSidebar
              projectId={projet.actif.id}
              activeId={chat?.conversationId ?? "default"}
              onSelect={chat?.onSelect ?? (() => {})}
              onNew={chat?.onNew ?? (() => {})}
            />
          ) : (
            <p className="px-3 py-3 text-xs text-zinc-500">
              Sélectionne un projet pour discuter avec son agent.
            </p>
          ))}
        {panel === "usage" && (
          // La colonne porte les réglages de la vue centrale (ticket-253) :
          // période, portée, et plafonds. Les chiffres eux-mêmes sont au centre.
          <PanneauUsage
            days={usage.days}
            setDays={usage.setDays}
            portee={usage.portee}
            setPortee={usage.setPortee}
            projetActifId={usage.projetActifId}
          />
        )}
      </div>
    </div>
  );
}
