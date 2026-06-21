import { useState } from "react";
import TicketCard from "./TicketCard";
import CreateTicketModal from "./CreateTicketModal";
import PlanEvolutionModal from "./PlanEvolutionModal";
import SkeletonList from "../SkeletonList";
import type { Project, Ticket, TicketStatus } from "../../types/api";

interface StatusGroup {
  status: TicketStatus;
  label: string;
  collapsible: boolean;
}

const STATUS_GROUPS: StatusGroup[] = [
  { status: "todo", label: "TODO", collapsible: false },
  { status: "in-progress", label: "IN PROGRESS", collapsible: false },
  { status: "in-review", label: "IN REVIEW", collapsible: false },
  { status: "blocked", label: "BLOCKED", collapsible: false },
  { status: "done", label: "DONE", collapsible: true },
  { status: "cancelled", label: "CANCELLED", collapsible: true },
];

interface TicketListProps {
  project: Project | null;
  byStatus: Record<TicketStatus, Ticket[]>;
  loading: boolean;
  error: string | null;
  activeTicket: Ticket | null;
  running: Set<string>;
  runningRound?: number;
  showKanban: boolean;
  onSelectTicket: (ticket: Ticket) => void;
  onRunPipeline: (ticketId: string) => void;
  onToggleKanban: () => void;
  onTicketCreated?: (ticket: Ticket) => void;
  onBatchCreated?: (tickets: Ticket[]) => void;
}

export default function TicketList({
  project,
  byStatus,
  loading,
  error,
  activeTicket,
  running,
  runningRound,
  showKanban,
  onSelectTicket,
  onRunPipeline,
  onToggleKanban,
  onTicketCreated,
  onBatchCreated,
}: TicketListProps) {
  const [collapsed, setCollapsed] = useState<Set<TicketStatus>>(
    new Set(["done", "cancelled"]),
  );
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showPlanModal, setShowPlanModal] = useState(false);

  if (!project) {
    return (
      <div className="p-4 text-zinc-500 text-xs">Select a project first</div>
    );
  }

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <div className="px-3 py-2 border-b border-zinc-700">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
            {project.name}
          </span>
        </div>
        <SkeletonList count={5} />
      </div>
    );
  }

  if (error) {
    return <div className="p-4 text-red-400 text-xs">{error}</div>;
  }

  function toggleGroup(status: TicketStatus) {
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(status)) next.delete(status);
      else next.add(status);
      return next;
    });
  }

  return (
    <>
      <div className="flex flex-col h-full">
        <div className="flex items-center justify-between px-3 py-2 border-b border-zinc-700 shrink-0">
          <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider truncate">
            {project.name}
          </span>
          <div className="flex items-center gap-1 shrink-0 ml-2">
            <button
              onClick={() => setShowPlanModal(true)}
              title="Planifier une évolution"
              aria-label="Planifier une évolution"
              className="w-6 h-6 flex items-center justify-center rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-sm leading-none"
            >
              ⚡
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              title="Nouveau ticket"
              aria-label="Créer un ticket"
              className="w-6 h-6 flex items-center justify-center rounded text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700 transition-colors text-base leading-none"
            >
              +
            </button>
            <button
              onClick={onToggleKanban}
              title={showKanban ? "List view" : "Kanban view"}
              className={`w-6 h-6 flex items-center justify-center rounded text-sm transition-colors ${
                showKanban
                  ? "bg-zinc-600 text-white"
                  : "text-zinc-500 hover:text-zinc-200 hover:bg-zinc-700"
              }`}
            >
              ≡
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-1">
          {STATUS_GROUPS.map(({ status, label, collapsible }) => {
            const tickets = byStatus[status];
            const isCollapsed = collapsed.has(status);

            return (
              <div key={status} className="mb-0.5">
                <button
                  onClick={() => collapsible && toggleGroup(status)}
                  className={`w-full flex items-center gap-1 px-3 py-1 text-[11px] font-semibold text-zinc-500 uppercase tracking-wider ${
                    collapsible
                      ? "hover:text-zinc-300 cursor-pointer"
                      : "cursor-default"
                  }`}
                >
                  {collapsible && (
                    <span className="text-[9px] w-2">
                      {isCollapsed ? "▶" : "▼"}
                    </span>
                  )}
                  {label}
                  <span className="ml-1 font-normal text-zinc-600 normal-case">
                    ({tickets.length})
                  </span>
                </button>

                {!isCollapsed &&
                  tickets.map((ticket) => (
                    <TicketCard
                      key={ticket.id}
                      ticket={ticket}
                      isActive={activeTicket?.id === ticket.id}
                      isRunning={running.has(ticket.id)}
                      runningRound={
                        running.has(ticket.id) ? runningRound : undefined
                      }
                      onSelect={onSelectTicket}
                      onRun={onRunPipeline}
                    />
                  ))}
              </div>
            );
          })}
        </div>
      </div>

      {showCreateModal && (
        <CreateTicketModal
          projectId={project.id}
          onClose={() => setShowCreateModal(false)}
          onCreated={(ticket) => {
            setShowCreateModal(false);
            onTicketCreated?.(ticket);
          }}
        />
      )}

      {showPlanModal && (
        <PlanEvolutionModal
          projectId={project.id}
          onClose={() => setShowPlanModal(false)}
          onBatchCreated={(tickets) => {
            setShowPlanModal(false);
            onBatchCreated?.(tickets);
          }}
        />
      )}
    </>
  );
}
