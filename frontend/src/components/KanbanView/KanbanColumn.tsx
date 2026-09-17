import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import TicketCard from "../Sidebar/TicketCard";
import type { Ticket, TicketStatus } from "../../types/api";

const STATUS_LABEL: Record<TicketStatus, string> = {
  todo: "TODO",
  "in-progress": "IN PROGRESS",
  "in-review": "IN REVIEW",
  done: "DONE",
  blocked: "BLOCKED",
  cancelled: "CANCELLED",
};

interface KanbanColumnProps {
  status: TicketStatus;
  tickets: Ticket[];
  activeTicket: Ticket | null;
  running: Set<string>;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
}

export default function KanbanColumn({
  status,
  tickets,
  activeTicket,
  running,
  onSelectTicket,
  onRunPipeline,
}: KanbanColumnProps) {
  return (
    <div className="flex flex-col flex-1 min-w-[200px] border-r border-zinc-700 last:border-r-0">
      <div className={`${BAND} border-b border-zinc-700 px-3`}>
        <RegionTitle taille="sm">
          {STATUS_LABEL[status]}
        </RegionTitle>
        <span className="ml-2 text-mini text-zinc-600">
          ({tickets.length})
        </span>
      </div>
      <div className="flex-1 overflow-y-auto py-1">
        {tickets.length === 0 ? (
          <div className="px-3 py-4 text-zinc-700 text-xs">—</div>
        ) : (
          tickets.map((ticket) => (
            <TicketCard
              key={ticket.id}
              ticket={ticket}
              isActive={activeTicket?.id === ticket.id}
              isRunning={running.has(ticket.id)}
              onSelect={onSelectTicket}
              onRun={onRunPipeline}
            />
          ))
        )}
      </div>
    </div>
  );
}
