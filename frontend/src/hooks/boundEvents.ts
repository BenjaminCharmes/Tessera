import type { OrchestratorEvent } from "../types/api";

/** Borne maximale du tableau `events` d'un run (ticket-353). */
export const MAX_EVENTS = 2000;

/**
 * Événements de contrôle toujours conservés dans `events`, même quand la
 * borne est atteinte. Ce sont eux que lisent les consommateurs de `events`
 * (issueDuRun, RunCard, useCockpit, BottomPanel).
 */
const CONTROL_EVENT_TYPES = new Set([
  "pipeline_done",
  "run_closed",
  "queue_progress",
  "pipeline_start",
]);

/**
 * Borne le tableau des événements à MAX_EVENTS en gardant toujours les
 * événements de contrôle, quel que soit leur âge (ticket-353).
 *
 * Les plus anciens événements ordinaires sont retirés en premier, de sorte
 * que `pipeline_done`, `run_closed`, `queue_progress` et `pipeline_start`
 * restent visibles dans le Pipeline log même après un long run.
 */
export function boundEvents(events: OrchestratorEvent[]): OrchestratorEvent[] {
  if (events.length <= MAX_EVENTS) return events;
  const toRemove = events.length - MAX_EVENTS;
  let removed = 0;
  return events.filter((ev) => {
    if (CONTROL_EVENT_TYPES.has(ev.type)) return true;
    if (removed < toRemove) {
      removed++;
      return false;
    }
    return true;
  });
}
