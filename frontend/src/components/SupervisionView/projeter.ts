import { INITIAL } from "../../hooks/streamState";
import type { StreamState, UseRunActifResult } from "../../hooks/streamState";
import type { UseSupervisionResult } from "../../hooks/useSupervision";

/**
 * Donne à `AgentPanel` l'interface qu'il attend, pour un run quelconque.
 *
 * `etat` est fourni par l'appelant (via `useEtatRun`) pour que les tokens
 * arrivent en temps réel sans attendre un re-rendu du parent (ticket-354).
 */
export function projeter(
  supervision: UseSupervisionResult,
  runId: string,
  etat: StreamState,
): UseRunActifResult {
  const rien = () => undefined;
  return {
    ...(etat ?? INITIAL),
    connect: rien,
    connectQueue: rien,
    connectAutonome: rien,
    disconnect: rien,
    // « Fermer » retire la carte du run clos de la liste (ticket-267).
    clear: () => supervision.fermerRun(runId),
    answer: (text: string) => supervision.envoyer(runId, { type: "answer", text }),
    interject: (text: string) => supervision.envoyer(runId, { type: "interject", text }),
    stop: () => supervision.envoyer(runId, { type: "stop", text: "" }),
  };
}
