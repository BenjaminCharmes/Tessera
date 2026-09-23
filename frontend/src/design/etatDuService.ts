import type { ServiceActif } from "../types/api";

/**
 * Comment se lit l'état d'un service — ticket-147.
 *
 * Deux endroits l'affichent : le panneau du projet, là où l'on lance, et la
 * bande de la Supervision, pour la vue d'ensemble. Ils lisent la même source
 * de données ; sans cette fonction ils dériveraient sur la **mise en forme**,
 * et c'est celle qu'on regarde le moins qui finirait fausse (ADR-034).
 *
 * ADR-026 : `blue` pour l'activité, `red` pour un échec, `zinc` au repos. Le
 * violet est réservé à l'identité — un service n'en est pas.
 */
export type EtatDuService = "en-cours" | "echoue" | "arrete" | "jamais-lance";

export function etatDuService(service: ServiceActif): EtatDuService {
  if (service.en_cours) return "en-cours";
  // L'arrêt demandé se **déclare**, il ne se déduit pas : `terminate()` laisse
  // un code non nul sur certaines plateformes, et déduire l'échec du code
  // afficherait une erreur là où l'utilisateur vient de cliquer « Arrêter »
  // (ticket-151).
  if (service.arrete_a_la_main) return "arrete";
  if ((service.code_de_sortie ?? 0) !== 0) return "echoue";
  // Jamais de `pid` : l'IDE ne l'a pas démarré. « À l'arrêt » se lisait comme
  // « je l'ai arrêté », alors que les serveurs qui font tourner l'IDE ont pu
  // être lancés à la main, hors de son registre (ticket-149).
  return service.pid === null ? "jamais-lance" : "arrete";
}

export function libelleDeLEtat(service: ServiceActif): string {
  switch (etatDuService(service)) {
    case "en-cours":
      return "en cours";
    case "echoue":
      return `arrêté — code ${service.code_de_sortie}`;
    case "jamais-lance":
      return "pas lancé par l'IDE";
    default:
      return "à l'arrêt";
  }
}

export function classeDeLEtat(service: ServiceActif): string {
  switch (etatDuService(service)) {
    case "en-cours":
      return "bg-blue-500/20 text-blue-200";
    case "echoue":
      return "bg-red-500/20 text-red-200";
    default:
      return "bg-zinc-800 text-zinc-400";
  }
}
