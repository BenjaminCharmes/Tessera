import { authorized } from "./auth";
import { API_ORIGIN } from "./config";

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

async function lireLesFenetres(): Promise<QuotaWindows> {
  const res = await fetch(`${API_ORIGIN}/api/v1/usage/quota`, authorized());
  if (!res.ok) {
    const texte = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${texte}`);
  }
  return res.json() as Promise<QuotaWindows>;
}

/** Lecture du quota par fenêtre. Un objet, pour qu'un test puisse l'espionner comme `api.*`. */
export const apiQuota = { fenetres: lireLesFenetres };
