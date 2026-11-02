import { request } from "./http";

/** Where a run stands — `GET /runs/{id}` (ticket-563). `restants` : tickets de file pas encore traités. */
export interface StatutDuRun {
  project_id: string;
  mode: string;
  statut: string;
  ticket_courant: string | null;
  approuves: string[];
  restants: string[];
  debut: string;
  fin: string | null;
  /** Tickets arrêtés dans ce run, avec la raison quand le backend la donne. */
  arretes: { ticket_id: string; motif: string | null }[];
}

// Ce fichier existe à part : `lib/api.ts` et `types/api.ts` sont sous cliquet
// de longueur (ticket-545) et ne peuvent plus grossir.
export const statutsDuRun = {
  /** Read the status of one run. */
  lire(runId: string): Promise<StatutDuRun> {
    return request(`/runs/${runId}`);
  },
};
