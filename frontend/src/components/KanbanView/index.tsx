import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import KanbanColumn from "./KanbanColumn";
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
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onPrCreated?: (ticketId: string, prNumber: number) => void;
}

export default function KanbanView({
  byStatus,
  activeTicket,
  running,
  githubRemote,
  onSelectTicket,
  onRunPipeline,
  onPrCreated,
}: KanbanViewProps) {
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
            onPrCreated={onPrCreated}
          />
        ))}
      </div>
    </div>
  );
}
