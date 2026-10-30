import { request } from "./http";

/** Une ligne de `GET /projects/{id}/usage/breakdown` : la dépense cumulée d'un rôle. */
export interface DepenseDuRole {
  role: string;
  total_cost_usd: number;
  total_tokens: number;
  call_count: number;
}

/** La ventilation du coût d'un projet ; seule la part par rôle sert au Bureau. */
export interface VentilationDuProjet {
  per_agent: DepenseDuRole[];
}

function lireLaVentilation(projectId: string): Promise<VentilationDuProjet> {
  return request(`/projects/${encodeURIComponent(projectId)}/usage/breakdown`);
}

/** Lecture du coût d'un projet par rôle. Un objet, pour qu'un test puisse l'espionner comme `api.*`. */
export const apiVentilation = { parProjet: lireLaVentilation };
