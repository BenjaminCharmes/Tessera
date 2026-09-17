import { IconCross, IconDot, IconExternal, IconPlay } from "../../design/icons";
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
  "in-review": "bg-amber-900 text-amber-300",
  done: "bg-green-900 text-green-300",
  blocked: "bg-red-900 text-red-300",
  cancelled: "bg-zinc-800 text-zinc-400",
};

const PRIORITY_STYLE: Record<TicketPriority, string> = {
  critical: "bg-red-900 text-red-300",
  high: "bg-amber-900 text-amber-300",
  medium: "bg-zinc-700 text-zinc-400",
  low: "bg-zinc-800 text-zinc-500",
};

// Pas d'icône ici : `CI_STYLE` porte déjà la couleur du rôle — ambre en
// attente, vert au succès, rouge à l'échec. Une émoji par-dessus répétait
// l'information et changeait de dessin selon la machine (ticket-067).
const CI_LABEL: Record<string, string> = {
  pending: "CI en cours",
  passing: "CI verte",
  failing: "CI en échec",
  none: "CI N/A",
};

const CI_STYLE: Record<string, string> = {
  pending: "bg-amber-900 text-amber-300 animate-pulse",
  passing: "bg-green-900 text-green-300",
  failing: "bg-red-900 text-red-300",
  none: "bg-zinc-700 text-zinc-400",
};

const PR_STATE_LABEL: Record<string, string> = {
  open: "PR ouverte",
  closed: "PR fermée",
  merged: "PR mergée",
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
          <div className="text-micro text-zinc-600 font-mono">{ticket.id}</div>
          <div className="text-xs text-zinc-200 leading-tight mt-0.5 line-clamp-2">
            {ticket.title}
          </div>
          <div className="flex items-center gap-1 mt-1 flex-wrap">
            <span
              className={`text-micro px-1.5 py-0.5 rounded font-medium ${STATUS_STYLE[ticket.status]}`}
            >
              {ticket.status}
            </span>
            <span
              className={`text-micro px-1.5 py-0.5 rounded font-medium ${PRIORITY_STYLE[ticket.priority]}`}
            >
              {ticket.priority}
            </span>
            {isRunning && runningRound != null && runningRound > 0 && (
              <span className="text-micro px-1.5 py-0.5 rounded font-medium bg-blue-900 text-blue-300 animate-pulse">
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
                className="text-micro px-1.5 py-0.5 rounded font-medium bg-zinc-800 text-zinc-300 hover:bg-zinc-700 transition-colors"
              >
                PR #{ticket.pr_number}
              </a>
            )}
            {prStatus && (
              <span
                className={`text-micro px-1.5 py-0.5 rounded font-medium ${CI_STYLE[prStatus.ci_status]}`}
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
                className="flex-1 min-w-0 text-micro bg-zinc-800 border border-zinc-600 rounded px-1.5 py-0.5 text-zinc-200 focus:outline-none focus:border-zinc-400"
              />
              <button
                type="submit"
                disabled={isCreatingPr || !headBranch.trim()}
                className="text-micro px-1.5 py-0.5 rounded bg-zinc-700 text-zinc-200 hover:bg-zinc-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                {isCreatingPr ? "…" : "OK"}
              </button>
              <button
                type="button"
                onClick={() => setShowPrForm(false)}
                title="Annuler"
                aria-label="Annuler"
                className="text-micro px-1 py-0.5 rounded text-zinc-500 hover:text-zinc-300 transition-colors"
              >
                <IconCross size={14} />
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
              title="Lancer le pipeline"
              aria-label="Lancer le pipeline"
              className="w-6 h-6 flex items-center justify-center rounded transition-colors text-zinc-500 hover:text-zinc-200 hover:bg-zinc-600 disabled:cursor-not-allowed"
            >
              {isRunning ? (
                <IconDot size={8} className="animate-pulse text-blue-400" />
              ) : (
                <IconPlay size={12} />
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
              aria-label="Ouvrir une PR"
              className="w-6 h-6 flex items-center justify-center rounded transition-colors text-zinc-500 hover:text-zinc-300 hover:bg-zinc-600"
            >
              <IconExternal size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
