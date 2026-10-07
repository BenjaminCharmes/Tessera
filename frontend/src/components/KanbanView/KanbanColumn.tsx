import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { useState } from "react";
import TicketCard from "../Sidebar/TicketCard";
import { MIME_TICKET, transitionPermise } from "../../lib/transitionsManuelles";
import type { Ticket, TicketStatus } from "../../types/api";

const STATUS_LABEL: Record<TicketStatus, string> = {
  todo: "TODO",
  "in-progress": "IN PROGRESS",
  "in-review": "IN REVIEW",
  done: "DONE",
  blocked: "BLOCKED",
  cancelled: "CANCELLED",
};

/** Colonnes pour lesquelles on limite le nombre de cartes affichées. */
const COLLAPSED_STATUSES: TicketStatus[] = ["done", "cancelled"];
const COLLAPSE_LIMIT = 30;

/** Extrait la partie numérique finale d'un identifiant de ticket. */
function ticketNumber(id: string): number {
  const m = id.match(/(\d+)$/);
  return m ? parseInt(m[1], 10) : 0;
}

interface KanbanColumnProps {
  status: TicketStatus;
  tickets: Ticket[];
  activeTicket: Ticket | null;
  running: Set<string>;
  githubRemote?: string | null;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  /** Un ticket déposé sur cette colonne y change de statut (ticket-194). */
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
  /**
   * La cause d'un blocage par ticket (ticket-218). Passé par `KanbanView`
   * qui le résout depuis l'API d'activité ; absent : aucune infobulle.
   */
  blockedArrets?: Record<string, string | null>;
  /** Identifiants en file — détermine le libellé du bouton par carte (ticket-284). */
  selection?: string[];
  /** Bascule l'appartenance d'un ticket à la file (ticket-284). */
  onToggleQueue?: (ticketId: string) => void;
}

export default function KanbanColumn({
  status,
  tickets,
  activeTicket,
  running,
  githubRemote,
  onSelectTicket,
  onRunPipeline,
  onChangeStatus,
  blockedArrets,
  selection,
  onToggleQueue,
}: KanbanColumnProps) {
  const [survol, setSurvol] = useState(false);
  const [showAll, setShowAll] = useState(false);

  const isCollapsible = COLLAPSED_STATUSES.includes(status);
  const totalCount = tickets.length;

  // Pour les colonnes collapsibles, on trie par numéro décroissant afin de
  // toujours afficher les tickets les plus récents en premier.
  const sorted = isCollapsible
    ? [...tickets].sort((a, b) => ticketNumber(b.id) - ticketNumber(a.id))
    : tickets;

  const shouldCollapse = isCollapsible && !showAll && totalCount > COLLAPSE_LIMIT;
  const visibleTickets = shouldCollapse ? sorted.slice(0, COLLAPSE_LIMIT) : sorted;
  const hiddenCount = shouldCollapse ? totalCount - COLLAPSE_LIMIT : 0;

  // `dragover` ne donne pas accès aux données, seulement aux types : on
  // accepte tout ticket, et c'est au dépôt que la transition se vérifie.
  function handleDragOver(e: React.DragEvent<HTMLDivElement>) {
    if (!onChangeStatus || !e.dataTransfer.types.includes(MIME_TICKET)) return;
    e.preventDefault();
    setSurvol(true);
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    setSurvol(false);
    if (!onChangeStatus) return;
    const brut = e.dataTransfer.getData(MIME_TICKET);
    if (!brut) return;
    e.preventDefault();
    let glisse: { id: string; status: TicketStatus };
    try {
      glisse = JSON.parse(brut) as { id: string; status: TicketStatus };
    } catch {
      return;
    }
    if (glisse.status === status || !transitionPermise(glisse.status, status)) return;
    onChangeStatus(glisse.id, status);
  }

  return (
    <div
      data-testid={`colonne-${status}`}
      onDragOver={handleDragOver}
      onDragLeave={() => setSurvol(false)}
      onDrop={handleDrop}
      className={`flex flex-col flex-1 min-w-[200px] border-r border-zinc-700 last:border-r-0 ${
        survol ? "bg-zinc-800/60" : ""
      }`}
    >
      <div className={`${BAND} border-b border-zinc-700 px-3`}>
        <RegionTitle taille="sm">
          {STATUS_LABEL[status]}
        </RegionTitle>
        <span className="ml-2 text-mini text-zinc-600">
          ({totalCount})
        </span>
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {totalCount === 0 ? (
          <div className="px-3 py-4 text-zinc-700 text-xs">—</div>
        ) : (
          <>
            {visibleTickets.map((ticket) => (
              <TicketCard
                key={ticket.id}
                ticket={ticket}
                isActive={activeTicket?.id === ticket.id}
                isRunning={running.has(ticket.id)}
                githubRemote={githubRemote}
                onSelect={onSelectTicket}
                onRun={onRunPipeline}
                onChangeStatus={onChangeStatus}
                arret={blockedArrets?.[ticket.id] ?? null}
                onToggleQueue={onToggleQueue}
                dansLaFile={selection?.includes(ticket.id) ?? false}
              />
            ))}
            {hiddenCount > 0 && (
              <button
                onClick={() => setShowAll(true)}
                className="w-full px-3 py-2 text-xs text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
              >
                Afficher les {hiddenCount} autres
              </button>
            )}
          </>
        )}
      </div>
    </div>
  );
}
