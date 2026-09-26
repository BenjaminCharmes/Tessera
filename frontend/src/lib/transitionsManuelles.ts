import type { TicketStatus } from "../types/api";

/**
 * Les statuts qu'un humain peut poser à la main — ticket-194.
 *
 * Jamais `in-progress` ni `in-review` : ces deux-là sont tenus par le
 * pipeline, et un ticket `in-progress` sans run se lirait comme un run
 * fantôme (ticket-177). Un `done` posé à la main dit « fait ailleurs » ; un
 * `cancelled` dit « on n'en veut plus » ; un retour en `todo` remet un
 * ticket bloqué ou clos dans la file.
 */
const TRANSITIONS: Record<TicketStatus, readonly TicketStatus[]> = {
  todo: ["done", "cancelled"],
  blocked: ["todo", "done", "cancelled"],
  done: ["todo"],
  cancelled: ["todo"],
  "in-progress": [],
  "in-review": [],
};

export function transitionsManuelles(depuis: TicketStatus): readonly TicketStatus[] {
  return TRANSITIONS[depuis];
}

export function transitionPermise(depuis: TicketStatus, vers: TicketStatus): boolean {
  return TRANSITIONS[depuis].includes(vers);
}

/** Le type MIME du ticket glissé entre deux colonnes du Kanban. */
export const MIME_TICKET = "application/x-tessera-ticket";
