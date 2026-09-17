import { BAND } from "../../design/layout";
import RegionTitle from "../../design/RegionTitle";
import { IconBlocked, IconCheck, IconDot } from "../../design/icons";
import { useState } from "react";
import type { PipelineRun } from "../../types/api";

interface RunHistoryProps {
  runs: PipelineRun[];
  loading: boolean;
  error: string | null;
  onSelectTicket?: (ticketId: string) => void;
}

function formatDuration(startedAt: string, finishedAt: string | null): string {
  if (!finishedAt) return "En cours…";
  const ms = new Date(finishedAt).getTime() - new Date(startedAt).getTime();
  if (ms < 0) return "—";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}m ${seconds.toString().padStart(2, "0")}s`;
}

function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleString("fr-FR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function StatusIcon({
  approved,
  finalStatus,
}: {
  approved: boolean | null;
  finalStatus: string | null;
}) {
  if (approved === true) return <IconCheck size={12} className="text-green-400" />;
  if (finalStatus === null)
    return <IconDot size={8} className="animate-pulse text-blue-400" />;
  return <IconBlocked size={12} className="text-red-400" />;
}

interface RunRowProps {
  run: PipelineRun;
  onSelectTicket?: (ticketId: string) => void;
}

function RunRow({ run, onSelectTicket }: RunRowProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border-b border-zinc-800">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-zinc-800 transition-colors"
      >
        <StatusIcon approved={run.approved} finalStatus={run.final_status} />
        <span className="flex-1 min-w-0 text-mini font-mono text-zinc-300 truncate">
          {run.ticket_id}
        </span>
        <span className="shrink-0 text-micro text-zinc-500">
          {run.rounds != null
            ? `${run.rounds} tour${run.rounds > 1 ? "s" : ""}`
            : "—"}
        </span>
        <span className="shrink-0 text-micro text-zinc-500 ml-1">
          {formatDuration(run.started_at, run.finished_at)}
        </span>
      </button>

      {expanded && (
        <div className="px-3 pb-3 space-y-1 bg-zinc-850">
          <div className="text-micro text-zinc-500">
            <span className="text-zinc-400">Début :</span>{" "}
            {formatTime(run.started_at)}
          </div>
          {run.finished_at && (
            <div className="text-micro text-zinc-500">
              <span className="text-zinc-400">Fin :</span>{" "}
              {formatTime(run.finished_at)}
            </div>
          )}
          <div className="text-micro text-zinc-500">
            <span className="text-zinc-400">Statut final :</span>{" "}
            {run.final_status ?? "En cours"}
          </div>
          {run.approved !== null && (
            <div className="text-micro text-zinc-500">
              <span className="text-zinc-400">Approuvé :</span>{" "}
              {run.approved ? "Oui" : "Non"}
            </div>
          )}
          {run.total_cost_usd > 0 && (
            <div className="text-micro text-zinc-500">
              <span className="text-zinc-400">Coût :</span>{" "}
              <span className="text-amber-400 font-mono">
                ${run.total_cost_usd.toFixed(4)}
              </span>
            </div>
          )}
          {onSelectTicket && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onSelectTicket(run.ticket_id);
              }}
              className="text-micro text-blue-400 hover:text-blue-300 underline mt-1"
            >
              Voir le ticket
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function RunHistory({
  runs,
  loading,
  error,
  onSelectTicket,
}: RunHistoryProps) {
  if (loading) {
    return (
      <div className="p-4 text-zinc-500 text-xs">Chargement des runs…</div>
    );
  }

  if (error) {
    return <div className="p-4 text-red-400 text-xs">{error}</div>;
  }

  if (runs.length === 0) {
    return (
      <div className="p-4 text-zinc-500 text-xs">
        Aucun pipeline exécuté pour ce projet.
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className={`${BAND} justify-between border-b border-zinc-700 px-3`}>
        <RegionTitle>
          Historique
        </RegionTitle>
        <span className="text-micro text-zinc-600">{runs.length} runs</span>
      </div>
      <div className="flex-1 overflow-y-auto">
        {runs.map((run) => (
          <RunRow key={run.id} run={run} onSelectTicket={onSelectTicket} />
        ))}
      </div>
    </div>
  );
}
