import BandeAutonome from "./BandeAutonome";
import QueueBar from "./QueueBar";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import {
  IconBoard,
  IconPlay,
  IconBolt,
  IconChevronDown,
  IconChevronRight,
  IconPlus,
} from "../../design/icons";
import { useState } from "react";
import TicketCard from "./TicketCard";
import CreateTicketModal from "./CreateTicketModal";
import PlanEvolutionModal from "./PlanEvolutionModal";
import SkeletonList from "../SkeletonList";
import type { Project, Ticket, TicketStatus } from "../../types/api";

interface StatusGroup {
  status: TicketStatus;
  label: string;
  collapsible: boolean;
}

const STATUS_GROUPS: StatusGroup[] = [
  { status: "todo", label: "TODO", collapsible: true },
  { status: "in-progress", label: "IN PROGRESS", collapsible: true },
  { status: "in-review", label: "IN REVIEW", collapsible: true },
  { status: "blocked", label: "BLOCKED", collapsible: true },
  { status: "done", label: "DONE", collapsible: true },
  { status: "cancelled", label: "CANCELLED", collapsible: true },
];

interface TicketListProps {
  project: Project | null;
  byStatus: Record<TicketStatus, Ticket[]>;
  loading: boolean;
  error: string | null;
  activeTicket: Ticket | null;
  running: Set<string>;
  runningRound?: number;
  maxRounds?: number | null;
  showKanban: boolean;
  /** Un run tourne, mais le centre montre autre chose (ticket-178). */
  runCache?: boolean;
  onVoirLeRun?: () => void;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onShowDiff?: (ticketId: string) => void;
  selection?: string[];
  onToggleQueue?: (ticketId: string) => void;
  onRunQueue?: () => void;
  onClearQueue?: () => void;
  onRunAutonome?: (options: { depuisGithub: boolean }) => void;
  queueEnCours?: boolean;
  onToggleKanban: () => void;
  onTicketCreated?: (ticket: Ticket) => void;
  onBatchCreated?: (tickets: Ticket[]) => void;
  onPrCreated?: (ticketId: string, prNumber: number) => void;
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
}

export default function TicketList({
  project,
  byStatus,
  loading,
  error,
  activeTicket,
  running,
  runningRound,
  maxRounds,
  showKanban,
  runCache,
  onVoirLeRun,
  onSelectTicket,
  onRunPipeline,
  onShowDiff,
  selection = [],
  onToggleQueue,
  onRunQueue,
  onClearQueue,
  onRunAutonome,
  queueEnCours = false,
  onToggleKanban,
  onTicketCreated,
  onBatchCreated,
  onPrCreated,
  onChangeStatus,
}: TicketListProps) {
  const [collapsed, setCollapsed] = useState<Set<TicketStatus>>(
    new Set(["done", "cancelled"]),
  );
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPlanModal, setShowPlanModal] = useState(false);

  if (!project) {
    return (
      <div className="p-4 text-zinc-500 text-xs">
        Sélectionne d'abord un projet
      </div>
    );
  }

  function toggleGroup(status: TicketStatus) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });
  }

  return (
    <>
      <div className="flex flex-col h-full">
        <div
          className={`${BAND} justify-between border-b border-zinc-700 px-3`}
        >
          {/* Pas le nom du projet : `ProjectHeader` le porte juste au-dessus,
              et il apparaissait deux fois à quarante pixels d'intervalle. */}
          <RegionTitle>Tickets</RegionTitle>
          <div className="flex items-center gap-1 shrink-0 ml-2">
            <button
              onClick={() => setShowPlanModal(true)}
              title="Planifier une évolution"
              aria-label="Planifier une évolution"
              className="w-6 h-6 flex items-center justify-center rounded-sm text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-sm leading-none"
            >
              <IconBolt size={14} />
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              title="Nouveau ticket"
              aria-label="Créer un ticket"
              className="w-6 h-6 flex items-center justify-center rounded-sm text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-base leading-none"
            >
              <IconPlus size={14} />
            </button>
            {/* Sans ce retour, quitter la vue du run la rendait injoignable
                depuis cet onglet jusqu'à la fin du run (ticket-178). */}
            {runCache && onVoirLeRun ? (
              <button
                onClick={onVoirLeRun}
                title="Revenir au run en cours"
                aria-label="Revenir au run en cours"
                className="flex h-6 w-6 items-center justify-center rounded-sm text-blue-300 transition-colors hover:bg-zinc-700"
              >
                <IconPlay size={14} />
              </button>
            ) : null}
            <button
              onClick={onToggleKanban}
              title={showKanban ? "Vue liste" : "Vue tableau"}
              className={`w-6 h-6 flex items-center justify-center rounded text-sm transition-colors ${
                showKanban
                  ? "bg-zinc-600 text-white"
                  : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700"
              }`}
            >
              <IconBoard size={14} />
            </button>
          </div>
        </div>

        <QueueBar
          selection={selection}
          onRun={onRunQueue ?? (() => {})}
          onClear={onClearQueue ?? (() => {})}
          enCours={queueEnCours}
        />

        {onRunAutonome && (
          <BandeAutonome
            selectionVide={selection.length === 0}
            githubLie={Boolean(project.github_remote)}
            enCours={queueEnCours}
            onLancer={onRunAutonome}
          />
        )}

        <div className="flex-1 overflow-y-auto py-1">
          {/* Le chargement et l'erreur remplacent la **liste**, pas le
              composant. Un retour anticipé ici démontait tout le sous-arbre —
              modales comprises — et un rafraîchissement des tickets suffisait
              à effacer le résultat du planificateur, qui est un appel facturé
              (ticket-071). */}
          {loading && <SkeletonList count={5} />}
          {error && !loading && (
            <p className="p-4 text-xs text-red-400">{error}</p>
          )}
          {!loading &&
            !error &&
            STATUS_GROUPS.map(({ status, label, collapsible }) => {
              const tickets = byStatus[status];
              const isCollapsed = collapsed.has(status);

              return (
                <div key={status} className="mb-0.5">
                  <button
                    onClick={() => collapsible && toggleGroup(status)}
                    className={`w-full flex items-center gap-1 px-3 py-1 text-mini font-semibold text-zinc-500 uppercase tracking-wider ${
                      collapsible
                        ? "hover:text-zinc-300 cursor-pointer"
                        : "cursor-default"
                    }`}
                  >
                    {collapsible && (
                      <span className="text-micro w-2">
                        {isCollapsed ? (
                          <IconChevronRight size={12} />
                        ) : (
                          <IconChevronDown size={12} />
                        )}
                      </span>
                    )}
                    {label}
                    <span className="ml-1 font-normal text-zinc-600 normal-case">
                      ({tickets.length})
                    </span>
                  </button>

                  {!isCollapsed &&
                    tickets.map((ticket) => (
                      <TicketCard
                        key={ticket.id}
                        ticket={ticket}
                        isActive={activeTicket?.id === ticket.id}
                        isRunning={running.has(ticket.id)}
                        runningRound={
                          running.has(ticket.id) ? runningRound : undefined
                        }
                        maxRounds={maxRounds}
                        githubRemote={project.github_remote}
                        onPrCreated={onPrCreated}
                        onChangeStatus={onChangeStatus}
                        onSelect={onSelectTicket}
                        onRun={onRunPipeline}
                        onShowDiff={onShowDiff}
                        onToggleQueue={onToggleQueue}
                        dansLaFile={selection.includes(ticket.id)}
                      />
                    ))}
                </div>
              );
            })}
        </div>
      </div>

      {showCreateModal && (
        <CreateTicketModal
          projectId={project.id}
          onClose={() => setShowCreateModal(false)}
          onCreated={(ticket) => {
            setShowCreateModal(false);
            onTicketCreated?.(ticket);
          }}
        />
      )}

      {showPlanModal && (
        <PlanEvolutionModal
          projectId={project.id}
          onClose={() => setShowPlanModal(false)}
          onBatchCreated={(tickets) => {
            setShowPlanModal(false);
            onBatchCreated?.(tickets);
          }}
        />
      )}
    </>
  );
}
