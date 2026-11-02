/**
 * Famille « étapes » du réducteur de `streamState.ts` (ticket-695) : les
 * événements qui ouvrent ou ferment une étape du pipeline. Chaque fonction de
 * famille rend le morceau d'état à fusionner, ou null quand l'événement n'est
 * pas de sa famille.
 */
import type { OrchestratorEvent } from "../types/api";
import type { StreamState } from "./streamState";

/** Ajoute une étape à la liste des étapes en cours (sans doublon). */
export function addEtapeEnCours(etapesEnCours: string[], etape: string): string[] {
  if (etapesEnCours.includes(etape)) return etapesEnCours;
  return [...etapesEnCours, etape];
}

/** Retire une étape de la liste des étapes en cours. */
export function removeEtapeEnCours(etapesEnCours: string[], etape: string): string[] {
  return etapesEnCours.filter((e) => e !== etape);
}

/** L'étape que l'événement de démarrage ouvre, ou null s'il n'en ouvre aucune. */
function etapeOuverte(type: string): string | null {
  switch (type) {
    case "security_audit_started":
      return "securite";
    case "validation_started":
      return "validation";
    case "documentation_started":
      return "documentation";
    case "livraison_started":
      return "livraison";
    default:
      return null;
  }
}

/** Les événements d'étape : ouverture (étape et liste), tests, fin de documentation. */
export function appliquerEtape(
  s: StreamState,
  ev: OrchestratorEvent,
): Partial<StreamState> | null {
  const ouverte = etapeOuverte(ev.type);
  if (ouverte !== null) {
    return { etape: ouverte, etapesEnCours: addEtapeEnCours(s.etapesEnCours, ouverte) };
  }
  switch (ev.type) {
    case "test_started": // le testeur ne dit rien tant que la suite tourne (ticket-587)
      return { etapesEnCours: addEtapeEnCours(s.etapesEnCours, "tests") };
    case "doc_updated":
    case "documentation_failed":
      return { etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "documentation") };
    default:
      return null;
  }
}
