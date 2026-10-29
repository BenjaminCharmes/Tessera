import { revueDeLEvenement, verdictDuReviewer } from "../../components/FilDuRun/verdict";
import type { StreamState } from "../../hooks/streamState";
import { ticketDuRun } from "./criteres";

/** Combien de boules de papier la corbeille dessine au plus. */
export const BOULES_MAX = 3;

export type BoulesDeLaCorbeille = 0 | 1 | 2 | 3;

/**
 * Les boules de la corbeille : une par `agent_done` du reviewer qui rend
 * `CHANGES_REQUESTED` sur le ticket en cours, trois au plus. `ticketEvents` repart de
 * zéro au ticket suivant, et un événement d'un autre ticket ne compte pas : la
 * corbeille se vide d'elle-même. Le refus du validateur n'y est pas : la copie rendue
 * le montre déjà (ticket-599).
 */
export function boulesDeLaCorbeille(etat: StreamState): BoulesDeLaCorbeille {
  const ticket = ticketDuRun(etat);
  const refus = etat.ticketEvents.filter(
    (ev) =>
      ev.type === "agent_done" &&
      ev.agent === "reviewer" &&
      (!ev.ticket_id || ev.ticket_id === ticket) &&
      verdictDuReviewer(revueDeLEvenement(ev)) === "CHANGES_REQUESTED",
  ).length;
  const n = Math.min(refus, BOULES_MAX);
  return n === 0 || n === 1 || n === 2 ? n : 3;
}
