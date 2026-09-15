import RoundBadge from "./RoundBadge";
import QuotaBadge from "./QuotaBadge";
import TicketActivity from "./TicketActivity";
import AgentBlock from "./AgentBlock";
import PipelineSummary from "./PipelineSummary";
import type { Project, Ticket } from "../../types/api";
import type { UseOrchestratorStreamResult } from "../../hooks/useOrchestratorStream";

interface AgentPanelProps {
  project: Project | null;
  stream: UseOrchestratorStreamResult;
  /** Ticket sélectionné, pour afficher ce qu'il a produit (ticket-064). */
  activeTicket?: Ticket | null;
}

export default function AgentPanel({
  project,
  stream,
  activeTicket = null,
}: AgentPanelProps) {
  const {
    status,
    ticketId,
    currentAgent,
    currentRound,
    currentTokens,
    lastResult,
    errorMessage,
    events,
    quota,
    clear,
  } = stream;

  const coderStarted = events.some(
    (e) => e.type === "agent_started" && e.agent === "codeur",
  );
  const reviewerStarted = events.some(
    (e) => e.type === "agent_started" && e.agent === "reviewer",
  );
  const coderDone = events.some(
    (e) => e.type === "agent_done" && e.agent === "codeur",
  );

  const reviewerContent =
    events
      .filter((e) => e.type === "agent_done" && e.agent === "reviewer")
      .map((e) =>
        typeof e.data["content"] === "string" ? e.data["content"] : "",
      )
      .at(-1) ?? "";

  const startTs = events.find((e) => e.type === "agent_started")?.timestamp;
  const endTs = events.find((e) => e.type === "pipeline_done")?.timestamp;
  const durationMs =
    startTs && endTs
      ? new Date(endTs).getTime() - new Date(startTs).getTime()
      : undefined;

  return (
    <div className="h-full flex flex-col bg-zinc-900 border-l border-zinc-700">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-zinc-700 shrink-0">
        <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider">
          Agents
          {ticketId && (
            <span className="ml-2 text-zinc-600 normal-case font-normal">
              — {ticketId}
            </span>
          )}
        </span>
        <div className="flex items-center gap-2">
          <QuotaBadge quota={quota} />
          {project && !ticketId && (
            <span className="text-xs text-zinc-600">{project.name}</span>
          )}
          {(status === "done" || status === "error") && (
            <button
              onClick={clear}
              title="Clear"
              className="text-zinc-600 hover:text-zinc-300 transition-colors text-sm"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto">
        {status === "idle" && (
          <div className="flex items-center justify-center h-full text-zinc-700 text-xs italic">
            {project ? "Run a ticket to start" : "Select a project"}
          </div>
        )}

        {status === "connecting" && (
          <div className="flex items-center justify-center h-full text-zinc-500 text-xs">
            <span className="animate-pulse">Connecting…</span>
          </div>
        )}

        {(status === "running" || status === "done") && (
          <>
            {currentRound > 0 && <RoundBadge current={currentRound} />}

            {coderStarted && (
              <AgentBlock
                agent="codeur"
                tokens={currentTokens}
                isActive={currentAgent === "codeur"}
                isDone={coderDone}
              />
            )}

            {reviewerStarted && (
              <AgentBlock
                agent="reviewer"
                tokens=""
                isActive={currentAgent === "reviewer"}
                isDone={status === "done"}
                reviewContent={reviewerContent}
              />
            )}

            {status === "done" && lastResult && (
              <PipelineSummary result={lastResult} durationMs={durationMs} />
            )}
          </>
        )}

        {status === "error" && (
          <div className="m-3 rounded p-3 bg-red-900/30 border border-red-700/50 text-red-400 text-xs">
            <div className="font-semibold mb-1">Erreur</div>
            <div>{errorMessage ?? "Unknown error"}</div>
          </div>
        )}
      </div>

      {/* Footer actions */}
      {(status === "done" || status === "error") && (
        <div className="px-4 py-3 border-t border-zinc-700 shrink-0 flex gap-3">
          <button
            onClick={clear}
            className="text-xs text-zinc-500 hover:text-zinc-200 transition-colors"
          >
            ✕ Fermer
          </button>
        </div>
      )}

      {/* Ce que le ticket a produit : runs, branche, PR (ticket-064). */}
      <TicketActivity
        projectId={project?.id ?? null}
        ticket={activeTicket}
        branch={lastResult?.branch ?? null}
      />
    </div>
  );
}
