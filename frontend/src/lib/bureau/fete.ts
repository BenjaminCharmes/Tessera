import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import { boiteAuxLettres } from "./boiteAuxLettres";
import type { ContourDeLaPiece } from "./contourDeLaPiece";

/** Combien de temps la pièce fête une PR mergée (ticket-598). */
export const DUREE_DE_LA_FETE_MS = 10_000;

/** L'indice du dernier événement de ce type, ou -1. */
export function indiceDuDernier(evenements: readonly OrchestratorEvent[], type: OrchestratorEvent["type"]): number {
  return evenements.map((ev) => ev.type).lastIndexOf(type);
}

/**
 * Vrai pendant `DUREE_DE_LA_FETE_MS` après un `ci_merge_done` `merged: true`.
 * L'horloge est celle de la vue : la fête s'éteint d'elle-même au tour suivant.
 */
export function enFete(etat: StreamState, maintenant: number): boolean {
  if (boiteAuxLettres(etat).etat !== "mergee") return false;
  const ci = etat.ticketEvents[indiceDuDernier(etat.ticketEvents, "ci_merge_done")];
  const depuis = maintenant - Date.parse(ci?.timestamp ?? "");
  // Un horodatage illisible (NaN) ne fête rien : on ne dessine que ce qu'on sait dater.
  return depuis >= 0 && depuis < DUREE_DE_LA_FETE_MS;
}

/**
 * Vrai tant que la boîte est `refusee` et qu'aucune livraison n'a redémarré
 * depuis : le `livraison_started` suivant éteint le gyrophare.
 */
export function gyrophareAllume(etat: StreamState): boolean {
  if (boiteAuxLettres(etat).etat !== "refusee") return false;
  const evenements = etat.ticketEvents;
  return indiceDuDernier(evenements, "livraison_started") < indiceDuDernier(evenements, "ci_merge_done");
}

/** Le contour de la pièce : la fête le passe au vert, le gyrophare au rouge. */
export function contourEnCelebration(
  contour: ContourDeLaPiece,
  fete: boolean,
  gyrophare: boolean,
): ContourDeLaPiece {
  if (gyrophare) return "rouge";
  return fete ? "vert" : contour;
}
