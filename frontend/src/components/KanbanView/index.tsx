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
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
}

export default function KanbanView({
  byStatus,
  activeTicket,
  running,
  onSelectTicket,
  onRunPipeline,
}: KanbanViewProps) {
  return (
    <div className="h-full flex flex-col bg-zinc-900">
      <div className="px-4 py-2 border-b border-zinc-700 shrink-0">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Kanban Board
        </span>
      </div>
      <div className="flex-1 flex overflow-x-auto overflow-y-hidden">
        {KANBAN_STATUSES.map((status) => (
          <KanbanColumn
            key={status}
            status={status}
            tickets={byStatus[status]}
            activeTicket={activeTicket}
            running={running}
            onSelectTicket={onSelectTicket}
            onRunPipeline={onRunPipeline}
          />
        ))}
      </div>
    </div>
  );
}
