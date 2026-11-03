import { revueDeLEvenement, verdictDuReviewer } from "../../components/FilDuRun/verdict";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import type { PosteId } from "./postesDuRun";

/** Combien de temps l'agent qui a renvoyé le travail reste au poste du codeur (ticket-599). */
export const DUREE_DE_LA_COPIE_MS = 15_000;

/** Qui rend sa copie, et pour quel tour du codeur. */
export interface RetourDeCopie {
  poste: Extract<PosteId, "reviewer" | "validateur">;
  tour: number;
}

function estCodeur(ev: OrchestratorEvent): boolean {
  return ev.type === "agent_started" && (ev.agent === "codeur" || ev.agent === "architect");
}

/** Le poste qui a renvoyé le travail dans cet événement, ou null si l'événement n'est pas un refus. */
function refusDe(ev: OrchestratorEvent): RetourDeCopie["poste"] | null {
  if (ev.type === "agent_done" && ev.agent === "reviewer") {
    return verdictDuReviewer(revueDeLEvenement(ev)) === "CHANGES_REQUESTED" ? "reviewer" : null;
  }
  if (ev.type === "validation_done") {
    const approuve = ev.data["approved"];
    // Sans champ `approved`, le verdict seul tranche ; un verdict illisible refuse.
    const accepte = typeof approuve === "boolean" ? approuve : ev.data["verdict"] === "APPROVED";
    return accepte ? null : "validateur";
  }
  return null;
}

function tourDuCodeur(evenements: readonly OrchestratorEvent[], indice: number): number {
  const annonce = evenements[indice]?.data["round"];
  if (typeof annonce === "number") return annonce;
  return evenements.slice(0, indice + 1).filter(estCodeur).length;
}

/**
 * Le dernier refus rendu entre deux départs du codeur : l'agent qui l'a émis
 * rapporte sa copie quand le codeur repart. Un premier départ n'en a aucun.
 */
function refusAvant(evenements: readonly OrchestratorEvent[], depart: number): RetourDeCopie["poste"] | null {
  for (let i = depart - 1; i >= 0; i -= 1) {
    const ev = evenements[i];
    if (ev === undefined || estCodeur(ev)) return null;
    const poste = refusDe(ev);
    if (poste !== null) return poste;
  }
  return null;
}

/**
 * Vrai pendant `DUREE_DE_LA_COPIE_MS` après le départ du codeur qui suit un
 * refus du reviewer ou du validateur. L'horloge est celle de la vue : le
 * retour à son poste se fait au tour suivant, sans minuteur propre.
 */
export function retourDeCopie(etat: StreamState, maintenant: number): RetourDeCopie | null {
  const evenements = etat.ticketEvents;
  const depart = evenements.map(estCodeur).lastIndexOf(true);
  if (depart < 0) return null;
  const poste = refusAvant(evenements, depart);
  if (poste === null) return null;
  const ecoule = maintenant - Date.parse(evenements[depart]?.timestamp ?? "");
  // Un horodatage illisible (NaN) ne montre rien : on ne dessine que ce qu'on sait dater.
  if (!(ecoule >= 0 && ecoule < DUREE_DE_LA_COPIE_MS)) return null;
  return { poste, tour: tourDuCodeur(evenements, depart) };
}

/** Ce qui peut empêcher le trajet : l'agent est ailleurs, ou la pièce est vide ou en fête. */
export interface ObstaclesDeLaCopie {
  faits: readonly PosteId[];
  absents: readonly PosteId[];
  clos: boolean;
  fete: boolean;
}

/**
 * Le retour de copie, s'il peut se dessiner : l'agent doit avoir fini (debout),
 * ne pas être chez le directeur ou aux RH, et la pièce ni close ni en fête.
 */
export function copieVisible(
  retour: RetourDeCopie | null,
  { faits, absents, clos, fete }: ObstaclesDeLaCopie,
): RetourDeCopie | null {
  if (retour === null || clos || fete) return null;
  if (!faits.includes(retour.poste) || absents.includes(retour.poste)) return null;
  return retour;
}

/** Ce que dit la pastille de la pièce pendant le trajet. */
export function libelleDeLaCopie(retour: RetourDeCopie): string {
  const qui = retour.poste === "reviewer" ? "le reviewer" : "le validateur";
  return `tour ${retour.tour} — ${qui} rend sa copie`;
}
