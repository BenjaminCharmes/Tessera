/**
 * Les réductions pures de la supervision — ticket-145.
 *
 * Extraites de `useSupervision`, qui dépassait deux cents lignes en accueillant
 * les services. Elles ne touchent ni socket ni état React, et se testent donc
 * sans monter de composant.
 */
import type { OrchestratorEvent, RunActif } from "../types/api";

/** Ce qu'on garde d'un service bavard : de quoi comprendre, pas tout. */
export const LIGNES_GARDEES = 200;

export function cleDuService(projectId: string, nom: string): string {
  return `${projectId}:${nom}`;
}

/** Garde la carte d'un run en phase avec ce qu'il annonce. */
export function majDesRuns(
  prec: RunActif[],
  ev: OrchestratorEvent,
  runId: string,
): RunActif[] {
  const connu = prec.some((r) => r.run_id === runId);
  if (!connu) {
    // Un run lancé pendant qu'on regarde : l'instantané ne l'avait pas, et
    // attendre le prochain rechargement pour l'afficher serait absurde.
    return [
      ...prec,
      {
        run_id: runId,
        project_id: ev.project_id ?? "",
        mode: "single",
        ticket_id: ev.ticket_id || null,
        etape: null,
        agent: ev.agent,
        tour: 0,
        tokens_entree: 0,
        tokens_sortie: 0,
        cout_usd: 0,
        verdict: null,
        demarre_a: ev.timestamp,
      },
    ];
  }
  return prec.map((r) =>
    r.run_id === runId
      ? {
          ...r,
          agent: ev.agent ?? r.agent,
          ticket_id: ev.ticket_id || r.ticket_id,
          etape: ev.type === "agent_started" ? ev.type : r.etape,
          tour:
            typeof ev.data["round"] === "number" ? ev.data["round"] : r.tour,
        }
      : r,
  );
}
