import type { Ticket, TicketPriority, TicketType } from "../types/api";
import { groupByStatus, type ByStatus } from "./ticketBoard";

/**
 * Filtrer, trier et chercher dans les tickets — ticket-195.
 *
 * Tout tient côté client : les tickets sont déjà chargés en entier, et
 * `ide-core` en a deux cents. Pure, pour être testée sans composant.
 */
export type TriDesTickets = "numero" | "priorite" | "date" | "statut";

export interface FiltresTickets {
  texte: string;
  type: TicketType | "";
  priorite: TicketPriority | "";
  agent: string;
  tri: TriDesTickets;
}

export const FILTRES_VIDES: FiltresTickets = {
  texte: "",
  type: "",
  priorite: "",
  agent: "",
  tri: "numero",
};

export const TRIS: readonly { valeur: TriDesTickets; label: string }[] = [
  { valeur: "numero", label: "Numéro" },
  { valeur: "priorite", label: "Priorité" },
  { valeur: "date", label: "Date" },
  { valeur: "statut", label: "Statut" },
];

const RANG_PRIORITE: Record<TicketPriority, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const RANG_STATUT: Record<Ticket["status"], number> = {
  "in-progress": 0,
  "in-review": 1,
  blocked: 2,
  todo: 3,
  done: 4,
  cancelled: 5,
};

function numero(t: Ticket): number {
  const m = /(\d+)/.exec(t.id);
  return m ? Number(m[1]) : 0;
}

export function filtresActifs(f: FiltresTickets): boolean {
  return f.texte.trim() !== "" || f.type !== "" || f.priorite !== "" || f.agent !== "";
}

export function appliquerFiltres(tickets: Ticket[], f: FiltresTickets): Ticket[] {
  const texte = f.texte.trim().toLowerCase();
  const retenus = tickets.filter((t) => {
    if (f.type && t.type !== f.type) return false;
    if (f.priorite && t.priority !== f.priorite) return false;
    if (f.agent && t.agent !== f.agent) return false;
    if (texte) {
      const corps = `${t.id} ${t.title} ${t.body}`.toLowerCase();
      if (!corps.includes(texte)) return false;
    }
    return true;
  });
  return trier(retenus, f.tri);
}

export function trier(tickets: Ticket[], tri: TriDesTickets): Ticket[] {
  const copie = [...tickets];
  switch (tri) {
    case "priorite":
      copie.sort(
        (a, b) => RANG_PRIORITE[a.priority] - RANG_PRIORITE[b.priority] || numero(a) - numero(b),
      );
      break;
    case "date":
      // Le plus récent d'abord : c'est celui qu'on vient d'écrire.
      copie.sort((a, b) => b.created.localeCompare(a.created) || numero(b) - numero(a));
      break;
    case "statut":
      copie.sort(
        (a, b) => RANG_STATUT[a.status] - RANG_STATUT[b.status] || numero(a) - numero(b),
      );
      break;
    default:
      copie.sort((a, b) => numero(a) - numero(b));
  }
  return copie;
}

/** Les tickets filtrés, regroupés par statut, et ce que les filtres cachent. */
export function filtrerParStatut(
  tickets: Ticket[],
  f: FiltresTickets,
): { byStatus: ByStatus; retenus: number; total: number } {
  const retenus = appliquerFiltres(tickets, f);
  return { byStatus: groupByStatus(retenus), retenus: retenus.length, total: tickets.length };
}
