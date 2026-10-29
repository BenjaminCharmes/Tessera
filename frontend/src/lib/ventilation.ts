import { authorized } from "./auth";
import { API_ORIGIN } from "./config";

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

async function lireLaVentilation(projectId: string): Promise<VentilationDuProjet> {
  const url = `${API_ORIGIN}/api/v1/projects/${encodeURIComponent(projectId)}/usage/breakdown`;
  const res = await fetch(url, authorized());
  if (!res.ok) {
    const texte = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${texte}`);
  }
  return res.json() as Promise<VentilationDuProjet>;
}

/** Lecture du coût d'un projet par rôle. Un objet, pour qu'un test puisse l'espionner comme `api.*`. */
export const apiVentilation = { parProjet: lireLaVentilation };
