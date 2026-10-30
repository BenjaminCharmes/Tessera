import { request } from "./http";

/** Le dernier relevé d'une fenêtre de quota, tel que `GET /usage/quota` le rend (ticket-558). */
export interface QuotaWindowReading {
  status: string;
  /** Fraction de la fenêtre consommée : 0.42 pour 42 %. */
  utilization: number;
  resets_at: string | null;
  observed_at: string;
}

/** Vide tant qu'aucun relevé n'est venu ; une fenêtre absente est une fenêtre inconnue. */
export interface QuotaWindows {
  windows: Record<string, QuotaWindowReading | undefined>;
}

function lireLesFenetres(): Promise<QuotaWindows> {
  return request("/usage/quota");
}

/** Lecture du quota par fenêtre. Un objet, pour qu'un test puisse l'espionner comme `api.*`. */
export const apiQuota = { fenetres: lireLesFenetres };
