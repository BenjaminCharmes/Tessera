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

interface KanbanColumnProps {
  status: TicketStatus;
  tickets: Ticket[];
  activeTicket: Ticket | null;
  running: Set<string>;
  githubRemote?: string | null;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onPrCreated?: (ticketId: string, prNumber: number) => void;
  /** Un ticket déposé sur cette colonne y change de statut (ticket-194). */
  onChangeStatus?: (ticketId: string, status: TicketStatus) => void;
}

export default function KanbanColumn({
  status,
  tickets,
  activeTicket,
  running,
  githubRemote,
  onSelectTicket,
  onRunPipeline,
  onPrCreated,
  onChangeStatus,
}: KanbanColumnProps) {
  const [survol, setSurvol] = useState(false);

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
              githubRemote={githubRemote}
              onPrCreated={onPrCreated}
              onSelect={onSelectTicket}
              onRun={onRunPipeline}
              onChangeStatus={onChangeStatus}
            />
          ))
        )}
      </div>
    </div>
  );
}
