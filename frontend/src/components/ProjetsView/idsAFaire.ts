import type { Ticket } from "../../types/api";

/** Les tickets à faire, dans l'ordre numérique de leurs ids (ticket-412). */
export function idsAFaire(tickets: Ticket[]): string[] {
  return tickets
    .filter((t) => t.status === "todo")
    .map((t) => t.id)
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}
