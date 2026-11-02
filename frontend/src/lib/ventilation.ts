import { request } from "./http";

/** Une ligne de `GET /projects/{id}/usage/breakdown` : la dépense cumulée d'un rôle. */
export interface DepenseDuRole {
  role: string;
  total_cost_usd: number;
  total_tokens: number;
  call_count: number;
}

/** La dépense cumulée d'un modèle, même route. */
export interface DepenseDuModele {
  model: string;
  total_cost_usd: number;
  total_tokens: number;
  call_count: number;
}

/** La dépense cumulée d'un projet ; seule la vue d'ensemble en remplit la liste. */
export interface DepenseDuProjet {
  project_id: string;
  total_cost_usd: number;
  total_tokens: number;
  call_count: number;
}

/** La ventilation du coût d'un projet, telle que le backend la rend ; le Bureau n'en lit que `per_agent`. */
export interface VentilationDuProjet {
  /** `null` pour la vue d'ensemble de tous les projets. */
  project_id: string | null;
  total_cost_usd: number;
  per_agent: DepenseDuRole[];
  per_model: DepenseDuModele[];
  per_project: DepenseDuProjet[];
}

function lireLaVentilation(projectId: string): Promise<VentilationDuProjet> {
  return request(`/projects/${encodeURIComponent(projectId)}/usage/breakdown`);
}

/** Lecture du coût d'un projet par rôle. Un objet, pour qu'un test puisse l'espionner comme `api.*`. */
export const apiVentilation = { parProjet: lireLaVentilation };
