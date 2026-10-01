import { useMemo } from "react";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconCross } from "../../design/icons";
import KanbanColumn from "./KanbanColumn";
import QueueBar from "../Sidebar/QueueBar";
import { useBlockedArrets } from "../../hooks/useBlockedArrets";
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
}

export default function KanbanView({
  byStatus,
  activeTicket,
  running,
  githubRemote,
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
}: KanbanViewProps) {
  const blockedIds = useMemo(
    () => byStatus["blocked"].map((t) => t.id),
    [byStatus],
  );
  const blockedArrets = useBlockedArrets(projectId ?? null, blockedIds);

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
      <div className="flex-1 flex overflow-x-auto overflow-y-hidden">
        {KANBAN_STATUSES.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            tickets={byStatus[status]}
            activeTicket={activeTicket}
            running={running}
            githubRemote={githubRemote}
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
