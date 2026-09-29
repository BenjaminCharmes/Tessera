import { useMemo } from "react";
import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import KanbanColumn from "./KanbanColumn";
import { useBlockedArrets } from "../../hooks/useBlockedArrets";
import type { Ticket, TicketStatus } from "../../types/api";

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
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
}

export default function KanbanView({
  byStatus,
  activeTicket,
  running,
  githubRemote,
  projectId,
  onSelectTicket,
  onRunPipeline,
  onChangeStatus,
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
          />
        ))}
      </div>
    </div>
  );
}
