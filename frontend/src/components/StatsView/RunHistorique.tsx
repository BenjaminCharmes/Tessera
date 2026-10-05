import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { applyEvent, INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent, RunEvent } from "../../types/api";
import RegionTitle from "../../design/RegionTitle";
import { IconHistory } from "../../design/icons";
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
  /** Libellé du bouton de fermeture : là d'où l'on vient (ticket-332). */
  libelleRetour?: string;
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
  libelleRetour = "Historique",
}: RunHistoriqueProps) {
  // Le résultat garde le run qu'il décrit : changer de run repasse en
  // chargement sans `setState` synchrone dans l'effet, que la règle
  // `react-hooks/set-state-in-effect` refuse.
  const [resultat, setResultat] = useState<{ runId: string; phase: Phase } | null>(null);
  const phase: Phase =
    resultat !== null && resultat.runId === runId ? resultat.phase : { kind: "loading" };

  useEffect(() => {
    let abandonne = false;
    api.runs
      .events(runId)
      .then((events) => {
        if (abandonne) return;
        const stream = events.map(toOrchestratorEvent).reduce(applyEvent, INITIAL);
        setResultat({ runId, phase: { kind: "done", stream } });
      })
      .catch((err: unknown) => {
        if (abandonne) return;
        const message = err instanceof Error ? err.message : String(err);
        setResultat({ runId, phase: { kind: "error", message } });
      });
    return () => {
      abandonne = true;
    };
  }, [runId]);

  return (
    <div className="flex h-full flex-col bg-zinc-900">
      <div className={`${BAND} justify-between gap-3 border-b border-zinc-700 px-4`}>
        <RegionTitle>Run {ticketId}</RegionTitle>
        <button
          type="button"
          onClick={onClose}
          className="inline-flex items-center gap-1 text-xs text-zinc-400 hover:text-zinc-200"
        >
          <IconHistory size={12} /> {libelleRetour}
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
                result={{
                  ...phase.stream.lastResult,
                  // Un run rejoué est terminé par construction : le ticket_id
                  // peut manquer dans les événements d'une file (ticket-327).
                  ticket_id: phase.stream.lastResult.ticket_id || ticketId,
                }}
                runClosed={true}
              />
            )}
          </>
        )}
      </div>
    </div>
  );
}
