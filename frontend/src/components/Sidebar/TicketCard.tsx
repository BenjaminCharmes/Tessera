import type { Ticket, TicketPriority, TicketStatus } from "../../types/api";

const STATUS_STYLE: Record<TicketStatus, string> = {
  todo: "bg-zinc-700 text-zinc-300",
  "in-progress": "bg-blue-900 text-blue-300",
  "in-review": "bg-yellow-900 text-yellow-300",
  done: "bg-green-900 text-green-300",
  blocked: "bg-red-900 text-red-300",
  cancelled: "bg-slate-800 text-slate-400",
};

const PRIORITY_STYLE: Record<TicketPriority, string> = {
  critical: "bg-red-900 text-red-300",
  high: "bg-orange-900 text-orange-300",
  medium: "bg-zinc-700 text-zinc-400",
  low: "bg-slate-800 text-slate-500",
};

interface TicketCardProps {
  ticket: Ticket;
  isActive: boolean;
  isRunning: boolean;
  runningRound?: number;
  onSelect: (ticket: Ticket) => void;
  onRun: (ticketId: string) => void;
}

export default function TicketCard({
  ticket,
  isActive,
  isRunning,
  runningRound,
  onSelect,
  onRun,
}: TicketCardProps) {
  const canRun = ticket.status !== "done" && ticket.status !== "cancelled";

  return (
    <div
      onClick={() => onSelect(ticket)}
      className={`relative mx-2 mb-1 p-2 rounded cursor-pointer transition-colors ${
        isActive ? "bg-zinc-700" : "hover:bg-zinc-800"
      }`}
    >
      <div className="flex items-start gap-1">
        <div className="flex-1 min-w-0">
          <div className="text-[10px] text-zinc-600 font-mono">{ticket.id}</div>
          <div className="text-xs text-zinc-200 leading-tight mt-0.5 line-clamp-2">
            {ticket.title}
          </div>
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${STATUS_STYLE[ticket.status]}`}
            >
              {ticket.status}
            </span>
            <span
              className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${PRIORITY_STYLE[ticket.priority]}`}
            >
              {ticket.priority}
            </span>
            {isRunning && runningRound != null && runningRound > 0 && (
              <span className="text-[10px] px-1.5 py-0.5 rounded font-medium bg-blue-900 text-blue-300 animate-pulse">
                tour {runningRound}/3
              </span>
            )}
          </div>
        </div>

        {canRun && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onRun(ticket.id);
            }}
            disabled={isRunning}
            title="Run pipeline"
            className="shrink-0 w-6 h-6 flex items-center justify-center rounded transition-colors text-zinc-500 hover:text-zinc-200 hover:bg-zinc-600 disabled:cursor-not-allowed"
          >
            {isRunning ? (
              <span className="text-blue-400 animate-pulse text-xs">●</span>
            ) : (
              <span className="text-[10px]">▶</span>
            )}
          </button>
        )}
      </div>
    </div>
  );
}
