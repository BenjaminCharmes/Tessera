import { request } from "./http";
import type { ActiviteDeService } from "../types/activiteProduit";

/**
 * Les agents que les apps vivantes déclarent dans leur fichier d'activité —
 * ticket-671. Hors de `api.ts`, qui a atteint son plafond de longueur.
 */
export function lireActivite(): Promise<ActiviteDeService[]> {
  return request("/services/running/activite");
}
