import type { TicketPriority, TicketStatus, TicketType } from "../types/tickets";

/*
 * Ce que l'interface écrit à la place des valeurs du modèle — ticket-735. Les
 * fichiers de ticket, l'API et le frontmatter gardent leurs valeurs anglaises
 * (ADR-044) ; l'écran parle français, et un seul endroit dit comment.
 */

export const STATUT_TICKET: Record<TicketStatus, string> = {
  todo: "À faire",
  "in-progress": "En cours",
  "in-review": "En revue",
  done: "Fait",
  blocked: "Bloqué",
  cancelled: "Annulé",
};

/** En tête de colonne ou de groupe : le pluriel. */
export const STATUT_TICKET_PLURIEL: Record<TicketStatus, string> = {
  todo: "À faire",
  "in-progress": "En cours",
  "in-review": "En revue",
  done: "Faits",
  blocked: "Bloqués",
  cancelled: "Annulés",
};

export const PRIORITE: Record<TicketPriority, string> = {
  critical: "Critique",
  high: "Haute",
  medium: "Moyenne",
  low: "Basse",
};

export const TYPE_DE_TICKET: Record<TicketType, string> = {
  feat: "Fonction",
  fix: "Correctif",
  chore: "Entretien",
  docs: "Docs",
  refactor: "Refonte",
  test: "Tests",
  design: "Conception",
};

const STATUT_RUN: Record<string, string> = {
  done: "Terminé",
  approved: "Approuvé",
  blocked: "Bloqué",
  interrupted: "Interrompu",
  failed: "Échoué",
  running: "En cours",
  cancelled: "Annulé",
  todo: "À faire",
  "in-progress": "En cours",
  "in-review": "En revue",
};

/** Le statut final d'un run, en français ; une valeur inconnue garde son identifiant. */
export function statutDuRun(statut: string): string {
  return STATUT_RUN[statut] ?? statut;
}
