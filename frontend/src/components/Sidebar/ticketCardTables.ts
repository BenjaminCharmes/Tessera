import type { EtatPastille } from "../../design/ui/StatusPill";
import type { TicketPriority, TicketStatus } from "../../types/api";

export const STATUS_STYLE: Record<TicketStatus, string> = {
  todo: "bg-zinc-700 text-zinc-300",
  "in-progress": "bg-blue-900 text-blue-300",
  "in-review": "bg-amber-900 text-amber-300",
  done: "bg-green-900 text-green-300",
  blocked: "bg-red-900 text-red-300",
  cancelled: "bg-zinc-800 text-zinc-400",
};

/** Correspondance de la charte : une priorité se lit comme un état. */
export const PRIORITY_ETAT: Record<TicketPriority, EtatPastille> = {
  critical: "echec",
  high: "attention",
  medium: "neutre",
  low: "neutre",
};

/** Le statut d'un ticket vu par `StatusPill` (select exclu, il garde son style). */
export const STATUS_ETAT: Record<TicketStatus, EtatPastille> = {
  todo: "neutre",
  "in-progress": "en-cours",
  "in-review": "attention",
  done: "reussi",
  blocked: "echec",
  cancelled: "neutre",
};

// Pas d'icône ici : `CI_ETAT` porte déjà la couleur du rôle — ambre en
// attente, vert au succès, rouge à l'échec. Une émoji par-dessus répétait
// l'information et changeait de dessin selon la machine (ticket-067).
export const CI_LABEL: Record<string, string> = {
  pending: "CI en cours",
  passing: "CI verte",
  failing: "CI en échec",
  none: "CI N/A",
  unreadable: "CI illisible",
};

export const CI_ETAT: Record<string, EtatPastille> = {
  pending: "attention",
  passing: "reussi",
  failing: "echec",
  none: "neutre",
  unreadable: "attention",
};

export const PR_STATE_LABEL: Record<string, string> = {
  open: "PR ouverte",
  closed: "PR fermée",
  merged: "PR mergée",
};
