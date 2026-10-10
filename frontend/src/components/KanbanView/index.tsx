import { useMemo } from "react";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconCross } from "../../design/icons";
import KanbanColumn from "./KanbanColumn";
import QueueBar from "../Sidebar/QueueBar";
import { useBlockedArrets } from "../../hooks/useBlockedArrets";
import { clePrDesTickets, usePrStatuses } from "../../hooks/usePrStatuses";
import { filtresActifs, type FiltresTickets } from "../../lib/filtresTickets";
import type { Ticket, TicketStatus, TicketUnreadable } from "../../types/api";

const KANBAN_STATUSES: TicketStatus[] = [
  "todo",
  "in-progress",
  "in-review",
  "blocked",
  "done",
];

interface KanbanViewProps {
  byStatus: Record<TicketStatus, Ticket[]>;
  activeTicket: Ticket | null;
  running: Set<string>;
  /** Dépôt distant du projet : sans lui, aucune carte ne propose de PR (ticket-123). */
  githubRemote?: string | null;
  /** Identifiant du projet actif, pour résoudre les arrêts des tickets bloqués (ticket-218). */
  projectId?: string | null;
  /** Fichiers de ticket que le backend n'a pas pu parser (ticket-210). */
  unreadable?: TicketUnreadable[];
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
  /** Identifiants des tickets en file — partagé avec la sidebar (ticket-284). */
  selection?: string[];
  /** Bascule l'appartenance d'un ticket à la file (ticket-284). */
  onToggleQueue?: (ticketId: string) => void;
  /** Lance la file courante (ticket-284). */
  onRunQueue?: () => void;
  /** Vide la file courante (ticket-284). */
  onClearQueue?: () => void;
  /** Un run de file est en cours — désactive le bouton « Lancer » (ticket-284). */
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

/** Returns labels for each active filter dimension, for display in the banner. */
function labelsDesFiltres(f: FiltresTickets): string[] {
  const labels: string[] = [];
  if (f.type) labels.push(`type ${f.type}`);
  if (f.priorite) labels.push(`priorité ${f.priorite}`);
  if (f.agent) labels.push(`agent ${f.agent}`);
  if (f.texte.trim()) labels.push(`texte « ${f.texte.trim()} »`);
  return labels;
}

export default function KanbanView({
  byStatus,
  activeTicket,
  running,
  projectId,
  unreadable = [],
  onSelectTicket,
  onRunPipeline,
  onChangeStatus,
  selection = [],
  onToggleQueue,
  onRunQueue,
  onClearQueue,
  queueEnCours = false,
  filtres,
  total,
  retenus,
  onClearFiltres,
}: KanbanViewProps) {
  const blockedIds = useMemo(
    () => byStatus["blocked"].map((t) => t.id),
    [byStatus],
  );
  const blockedArrets = useBlockedArrets(projectId ?? null, blockedIds);
  const clePr = useMemo(
    () => clePrDesTickets(Object.values(byStatus).flat()),
    [byStatus],
  );
  const prStatuses = usePrStatuses(projectId ?? null, clePr);

  return (
    <div className="h-full flex flex-col bg-zinc-900">
      <div className={`${BAND} border-b border-zinc-700 px-4`}>
        <RegionTitle>
          Kanban Board
        </RegionTitle>
      </div>
      {!!(onToggleQueue ?? onRunQueue ?? onClearQueue) && (
        <QueueBar
          selection={selection}
          onRun={onRunQueue ?? (() => {})}
          onClear={onClearQueue ?? (() => {})}
          enCours={queueEnCours}
        />
      )}
      {filtres && filtresActifs(filtres) && total !== undefined && retenus !== undefined && (
        <div
          className="flex items-center gap-2 border-b border-zinc-700 bg-zinc-800/60 px-4 py-1.5"
          data-testid="kanban-filtre-bandeau"
        >
          <span className="text-xs text-zinc-400">
            Filtres :{" "}
            <span className="text-zinc-300">{labelsDesFiltres(filtres).join(" · ")}</span>
          </span>
          <span
            className="text-xs text-amber-400"
            data-testid="kanban-filtre-compte"
          >
            {retenus} ticket{retenus !== 1 ? "s" : ""} sur {total}
          </span>
          <button
            type="button"
            onClick={onClearFiltres}
            className="ml-auto text-xs text-zinc-500 hover:text-zinc-300"
          >
            Effacer les filtres
          </button>
        </div>
      )}
      <div className="flex-1 flex overflow-x-auto overflow-y-hidden">
        {KANBAN_STATUSES.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            tickets={byStatus[status]}
            activeTicket={activeTicket}
            running={running}
            prStatuses={prStatuses}
            onSelectTicket={onSelectTicket}
            onRunPipeline={onRunPipeline}
            onChangeStatus={onChangeStatus}
            blockedArrets={status === "blocked" ? blockedArrets : undefined}
            selection={selection}
            onToggleQueue={onToggleQueue}
          />
        ))}
      </div>
      {unreadable.length > 0 && (
        <div
          className="border-t border-zinc-700 px-4 py-2"
          data-testid="kanban-unreadable"
        >
          <p className="text-xs text-red-400 font-medium mb-1">
            {unreadable.length} fichier{unreadable.length > 1 ? "s" : ""} illisible{unreadable.length > 1 ? "s" : ""}
          </p>
          <ul className="space-y-0.5">
            {unreadable.map((u) => (
              <li
                key={u.file_path}
                className="text-xs text-zinc-500"
                title={u.error}
                data-testid="kanban-unreadable-item"
              >
                <IconCross size={10} className="mr-1 inline text-red-500" />
                <span className="font-mono">{u.file_path.split(/[\\/]/).pop()}</span>
                <span className="ml-2 text-zinc-600">— {u.error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
