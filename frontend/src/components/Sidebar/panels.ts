/**
 * Les destinations de la barre de navigation.
 *
 * Extrait d'`index.tsx` pour que `NavRail` puisse s'y référer sans importer
 * la sidebar complète — et donc sans tirer tout l'arbre des panneaux dans le
 * test de la barre.
 */
export const PANNEAUX = [
  "projects",
  "tickets",
  "files",
  "history",
  "agents",
  "usage",
  "supervision",
] as const;

export type SidebarPanel = (typeof PANNEAUX)[number];

/**
 * Ce qui, dans la supervision, merite d'etre vu avant le reste — ticket-129.
 *
 * `null` est le cas nominal : des runs tournent, et c'est tout. ADR-026 :
 * l'ambre pour une attente, le rouge pour un echec, le bleu pour l'activite.
 */
export type AlerteDeSupervision = "attente" | "bloque" | null;
