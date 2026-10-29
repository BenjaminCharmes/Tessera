import type { StreamState } from "../../hooks/streamState";
import type { EventType } from "../../types/api";

/**
 * Les événements que la documentation émet elle-même, ou qui passent pendant qu'elle
 * tourne sans rien dire de la suite du run : ils ne la referment pas.
 */
const NEUTRES: readonly EventType[] = [
  "documentation_started",
  "agent_token",
  "agent_tool_use",
  "quota_updated",
  "provider_fallback",
];

/**
 * La documentation par lot tourne-t-elle (ADR-035) ? Elle s'ouvre à `documentation_started`
 * et se ferme à `doc_updated` ou `documentation_failed`. Sans fichier changé ni refus,
 * aucun événement de fin n'est émis : le premier événement suivant qui n'est pas neutre
 * la referme alors. Un run clos n'a plus personne à la bibliothèque.
 */
export function documentationEnCours(etat: StreamState): boolean {
  if (etat.runClosed) return false;
  const debut = etat.ticketEvents.findLastIndex((ev) => ev.type === "documentation_started");
  if (debut < 0) return false;
  return etat.ticketEvents.slice(debut + 1).every((ev) => NEUTRES.includes(ev.type));
}

/**
 * La phase 1 de la livraison (rebase, tests, PR) tourne-t-elle ? Elle va de
 * `livraison_started` à `livraison_done` ; la phase 2, la CI, n'est pas la dépose.
 */
export function livraisonEnCours(etat: StreamState): boolean {
  if (etat.runClosed) return false;
  const evenements = etat.ticketEvents;
  const debut = evenements.findLastIndex((ev) => ev.type === "livraison_started");
  if (debut < 0) return false;
  return !evenements.slice(debut + 1).some((ev) => ev.type === "livraison_done");
}
