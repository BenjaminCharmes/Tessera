import { request } from "./api";
import type { SalleTessera } from "../types/salleTessera";

/**
 * La salle des serveurs de Tessera — ticket-726. Hors de `api.ts`, qui a atteint
 * son plafond de longueur, comme `apiActivite`.
 */
export function lireLaSalleTessera(): Promise<SalleTessera> {
  return request("/tessera/salle");
}
