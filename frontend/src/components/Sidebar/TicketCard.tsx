import { useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import type {
  PRStatus,
  Ticket,
  TicketPriority,
  TicketStatus,
} from "../../types/api";

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

const CI_LABEL: Record<string, string> = {
  pending: "⏳ CI",
  passing: "✅ CI",
  failing: "❌ CI",
  none: "CI N/A",
};

const CI_STYLE: Record<string, string> = {
  pending: "bg-yellow-900 text-yellow-300 animate-pulse",
  passing: "bg-green-900 text-green-300",
  failing: "bg-red-900 text-red-300",
  none: "bg-zinc-700 text-zinc-400",
};

const PR_STATE_LABEL: Record<string, string> = {
  open: "PR ouverte",
  closed: "PR fermée",
  merged: "🔀 Mergée",
};

const POLL_INTERVAL_MS = 30_000;

interface TicketCardProps {
  ticket: Ticket;
  isActive: boolean;
  isRunning: boolean;
  runningRound?: number;
  githubRemote?: string | null;
  onSelect: (ticket: Ticket) => void;
  onRun: (ticketId: string) => void;
  onPrCreated?: (ticketId: string, prNumber: number) => void;
}

export default function TicketCard({
  ticket,
  isActive,
  isRunning,
  runningRound,
  githubRemote,
  onSelect,
  onRun,
  onPrCreated,
}: TicketCardProps) {
  const canRun = ticket.status !== "done" && ticket.status !== "cancelled";
  const canOpenPr =
    ticket.status === "done" && !!githubRemote && ticket.pr_number === null;

  const [showPrForm, setShowPrForm] = useState(false);
  const [headBranch, setHeadBranch] = useState(ticket.id);
  const [isCreatingPr, setIsCreatingPr] = useState(false);
  const [prStatus, setPrStatus] = useState<PRStatus | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!ticket.pr_number || !githubRemote) return;

    const fetchStatus = async () => {
      try {
        const s = await api.github.getPrStatus(ticket.project_id, ticket.id);
        setPrStatus(s);
        if (s.state === "merged" || s.state === "closed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch {
        // ignore transient errors
      }
    };

    fetchStatus();
    intervalRef.current = setInterval(fetchStatus, POLL_INTERVAL_MS);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [ticket.pr_number, ticket.project_id, ticket.id, githubRemote]);

  async function handleCreatePr(e: React.FormEvent) {
    e.preventDefault();
    e.stopPropagation();
    setIsCreatingPr(true);
    try {
      const result = await api.github.createPr(
        ticket.project_id,
        ticket.id,
        headBranch,
      );
      setShowPrForm(false);
      onPrCreated?.(ticket.id, result.pr_number);
    } catch {
      // errors will surface via toast at the caller level
    } finally {
      setIsCreatingPr(false);
    }
  }

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
            {ticket.pr_number !== null && (
              <a
                href={prStatus?.pr_url ?? "#"}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                title={
                  prStatus
                    ? PR_STATE_LABEL[prStatus.state]
                    : `PR #${ticket.pr_number}`
                }
                className="text-[10px] px-1.5 py-0.5 rounded font-medium bg-purple-900 text-purple-300 hover:bg-purple-800 transition-colors"
              >
                PR #{ticket.pr_number}
              </a>
            )}
            {prStatus && (
              <span
                className={`text-[10px] px-1.5 py-0.5 rounded font-medium ${CI_STYLE[prStatus.ci_status]}`}
              >
                {CI_LABEL[prStatus.ci_status]}
              </span>
            )}
          </div>
          {showPrForm && (
            <form
              onSubmit={handleCreatePr}
              onClick={(e) => e.stopPropagation()}
              className="mt-1.5 flex gap-1"
            >
              <input
                autoFocus
                type="text"
                value={headBranch}
                onChange={(e) => setHeadBranch(e.target.value)}
                placeholder="branch name"
                className="flex-1 min-w-0 text-[10px] bg-zinc-800 border border-zinc-600 rounded px-1.5 py-0.5 text-zinc-200 focus:outline-none focus:border-zinc-400"
              />
              <button
                type="submit"
                disabled={isCreatingPr || !headBranch.trim()}
                className="text-[10px] px-1.5 py-0.5 rounded bg-purple-700 text-purple-100 hover:bg-purple-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isCreatingPr ? "…" : "OK"}
              </button>
              <button
                type="button"
                onClick={() => setShowPrForm(false)}
                className="text-[10px] px-1 py-0.5 rounded text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                ✕
              </button>
            </form>
          )}
        </div>

        <div className="flex flex-col gap-0.5 shrink-0">
          {canRun && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onRun(ticket.id);
              }}
              disabled={isRunning}
              title="Run pipeline"
              className="w-6 h-6 flex items-center justify-center rounded transition-colors text-zinc-500 hover:text-zinc-200 hover:bg-zinc-600 disabled:cursor-not-allowed"
            >
              {isRunning ? (
                <span className="text-blue-400 animate-pulse text-xs">●</span>
              ) : (
                <span className="text-[10px]">▶</span>
              )}
            </button>
          )}
          {canOpenPr && !showPrForm && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowPrForm(true);
              }}
              title="Ouvrir une PR"
              className="w-6 h-6 flex items-center justify-center rounded transition-colors text-zinc-500 hover:text-purple-300 hover:bg-zinc-600"
            >
              <span className="text-[10px]">↗</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
