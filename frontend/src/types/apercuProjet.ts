import type { StripeMode } from "./api";

// Sortis d'`api.ts`, qui touchait son plafond de longueur (ticket-633).

/** Nombre de fiches par statut, tel que `/projects/overview` le rend (ticket-398). */
export interface TicketCounts {
  todo: number;
  in_progress: number;
  in_review: number;
  blocked: number;
  done: number;
}

export interface ProjectOverview {
  id: string;
  name: string;
  category: string | null;
  description: string;
  github_remote: string | null;
  /** Date ISO du premier commit du dossier, sinon de création du dossier. */
  created_at: string;
  /** Date ISO du dernier commit du dossier — null sans dépôt git. */
  last_activity: string | null;
  tickets: TicketCounts;
  /** Un run est ouvert sur le projet. */
  run_actif: boolean;
  /** Le projet porte une icône servie par `/projects/{id}/icon`. */
  icon: boolean;
  /** `agents.json` déclare au moins un service lançable. */
  services_declares: boolean;
  /** Au moins un service du projet tourne en ce moment. */
  services_en_cours: boolean;
  /** `agents.json` déclare un bloc `online` : la carte offre « Mettre en ligne » (ticket-472). */
  online_declared: boolean;
  /** Le domaine déclaré, nommé par la confirmation. */
  online_domain?: string | null;
  /** Le mode Stripe déclaré ; `null` sans bloc `stripe`. */
  online_stripe_mode?: StripeMode | null;
  /** Les runs du projet tournent dans un worktree (ADR-056) : un ticket à la fois, pas de file (ticket-633). */
  worktree?: boolean;
  /** Incohérences relevées au chargement (ex. `project_id` qui ne suit pas le dossier). */
  avertissements?: string[];
}
