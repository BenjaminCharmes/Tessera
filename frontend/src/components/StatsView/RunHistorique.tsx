import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { applyEvent, INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent, RunEvent } from "../../types/api";
import RegionTitle from "../../design/RegionTitle";
import { BAND } from "../../design/layout";
import FilDuRun from "../FilDuRun";
import PipelineSummary from "../AgentPanel/PipelineSummary";

// ---------------------------------------------------------------------------
// Conversion RunEvent → OrchestratorEvent
// ---------------------------------------------------------------------------

/**
 * Convertit un événement stocké en BDD vers la forme attendue par `applyEvent`.
 *
 * Le REST endpoint (ticket-280) renvoie {type, agent, data, timestamp} ;
 * `applyEvent` attend en plus `ticket_id`, récupéré depuis `ev.data` si présent.
 */
function toOrchestratorEvent(ev: RunEvent): OrchestratorEvent {
  const ticketId =
    typeof ev.data["ticket_id"] === "string" ? ev.data["ticket_id"] : "";
  return {
    type: ev.type,
    agent: ev.agent as OrchestratorEvent["agent"],
    ticket_id: ticketId,
    data: ev.data,
    timestamp: ev.timestamp,
  };
}

// ---------------------------------------------------------------------------
// RunHistorique
// ---------------------------------------------------------------------------

interface RunHistoriqueProps {
  runId: string;
  ticketId: string;
  /** Appelé quand l'utilisateur ferme la vue et revient à l'historique. */
  onClose: () => void;
}

type Phase =
  | { kind: "loading" }
  | { kind: "error"; message: string }
  | { kind: "done"; stream: StreamState };

/**
 * Vue en lecture seule d'un run terminé, construite en rejouant ses événements
 * dans `applyEvent` — ticket-281.
 *
 * Ni bouton d'arrêt, ni champ de message, ni chronomètre : le run est fini.
 */
export default function RunHistorique({
  runId,
  ticketId,
  onClose,
}: RunHistoriqueProps) {
  const [phase, setPhase] = useState<Phase>({ kind: "loading" });

  useEffect(() => {
    setPhase({ kind: "loading" });
    api.runs
      .events(runId)
      .then((events) => {
        const stream = events.map(toOrchestratorEvent).reduce(applyEvent, INITIAL);
        setPhase({ kind: "done", stream });
      })
      .catch((err: unknown) => {
        const message = err instanceof Error ? err.message : String(err);
        setPhase({ kind: "error", message });
      });
  }, [runId]);

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>Run {ticketId}</RegionTitle>
        <button
          type="button"
          onClick={onClose}
          className="text-xs text-zinc-400 hover:text-zinc-200"
        >
          ← Historique
        </button>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto py-3">
        {phase.kind === "loading" && (
          <p className="px-4 text-xs text-zinc-500">Chargement…</p>
        )}
        {phase.kind === "error" && (
          <p
            className="px-4 text-xs text-red-400"
            data-testid="run-historique-erreur"
          >
            {phase.message}
          </p>
        )}
        {phase.kind === "done" && (
          <>
            {phase.stream.entries.length === 0 && (
              <p className="px-4 text-xs text-zinc-500">
                Aucun agent enregistré pour ce run.
              </p>
            )}
            <FilDuRun entries={phase.stream.entries} />
            {phase.stream.lastResult && (
              <PipelineSummary
                result={phase.stream.lastResult}
                runClosed={phase.stream.runClosed}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
