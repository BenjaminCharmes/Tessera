/**
 * Les destinations de la barre de navigation.
 *
 * Extrait d'`index.tsx` pour que `NavRail` puisse s'y référer sans importer
 * la sidebar complète — et donc sans tirer tout l'arbre des panneaux dans le
 * test de la barre.
 */
export type SidebarPanel =
  | "projects"
  | "tickets"
  | "history"
  | "agents"
  | "usage";
