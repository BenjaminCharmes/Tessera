import { useMemo } from "react";
import { api } from "../lib/api";
import { lignesDuBilan } from "../lib/bureau/bilanDeLAgent";
import type { LigneDeLAgent } from "../lib/bureau/agentChoisi";
import { apiVentilation } from "../lib/ventilation";
import type { VentilationDuProjet } from "../lib/ventilation";
import type { PipelineRun } from "../types/api";
import { useResource } from "./useResource";

/** Comme `useWeekEmployee` : `GET /projects/{id}/runs` plafonne à 100, de quoi couvrir une semaine. */
const RUNS_DU_PROJET = 100;

/**
 * Le bilan de l'agent choisi (ticket-630) : ses runs de la semaine et son coût
 * cumulé sur le projet. Les deux lectures sont indépendantes : l'une qui échoue
 * retire sa ligne et laisse l'autre. `projet` à `null` : rien n'est lu.
 */
export function useBilanDeLAgent(
  projet: string | null,
  role: string | null,
  maintenant: number,
): LigneDeLAgent[] {
  const lireRuns = useMemo(
    () => (projet === null ? null : () => api.runs.list(projet, RUNS_DU_PROJET)),
    [projet],
  );
  const lireCout = useMemo(
    () => (projet === null ? null : () => apiVentilation.parProjet(projet)),
    [projet],
  );
  const runs = useResource<PipelineRun[] | null>(lireRuns, null);
  const cout = useResource<VentilationDuProjet | null>(lireCout, null);

  return useMemo(
    () => (role === null ? [] : lignesDuBilan(runs.data, cout.data, role, maintenant)),
    [runs.data, cout.data, role, maintenant],
  );
}
