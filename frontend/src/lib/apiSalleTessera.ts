import { request } from "./http";
import type { SalleTessera } from "../types/salleTessera";

/**
 * La salle des serveurs de Tessera — ticket-726. Hors de `api.ts`, qui a atteint
 * son plafond de longueur, comme `apiActivite`.
 */
export function lireLaSalleTessera(lignesDuJournal?: number): Promise<SalleTessera> {
  return request(lignesDuJournal === undefined ? "/tessera/salle" : `/tessera/salle?journal=${lignesDuJournal}`);
}
