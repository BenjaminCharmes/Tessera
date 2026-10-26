import { authorized } from "./auth";
import { API_ORIGIN } from "./config";

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
}

// Ce fichier existe à part : `lib/api.ts` et `types/api.ts` sont sous cliquet
// de longueur (ticket-545) et ne peuvent plus grossir.
export const statutsDuRun = {
  /** Read the status of one run. */
  async lire(runId: string): Promise<StatutDuRun> {
    const res = await fetch(`${API_ORIGIN}/api/v1/runs/${runId}`, authorized());
    if (!res.ok) throw new Error(`API ${res.status}: ${await res.text().catch(() => res.statusText)}`);
    return res.json() as Promise<StatutDuRun>;
  },
};
