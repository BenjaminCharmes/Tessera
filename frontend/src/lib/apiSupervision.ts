import { request } from "./http";
import type { RecapSupervision } from "../types/supervision";

/**
 * Le récap du superviseur — ticket-861. Hors de `api.ts`, qui a atteint son
 * plafond de longueur, comme `apiSalleTessera`. Lecture seule : la route ne
 * donne aucun pouvoir.
 */
export function lireLeRecap(depuis: string | null): Promise<RecapSupervision> {
  return request(depuis === null ? "/supervision/recap" : `/supervision/recap?depuis=${encodeURIComponent(depuis)}`);
}
