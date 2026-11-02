export type TicketStatus = "todo" | "in-progress" | "in-review" | "done" | "blocked" | "cancelled";

// Doit rester aligné sur TicketType côté backend
// (backend/src/tessera/models/ticket.py) : types Conventional Commits
// + `design`, propre à Tessera.
export type TicketType = "feat" | "fix" | "chore" | "docs" | "refactor" | "test" | "design";
export type TicketPriority = "critical" | "high" | "medium" | "low";

export interface Ticket {
  id: string;
  title: string;
  type: TicketType;
  status: TicketStatus;
  priority: TicketPriority;
  agent: string;
  depends_on: string[];
  created: string;
  github_issue_url: string | null;
  pr_number: number | null;
  body: string;
  project_id: string;
  file_path: string;
}

/** A ticket file the backend could not parse (ticket-210). */
export interface TicketUnreadable {
  file_path: string;
  error: string;
}

/** Full response from GET /projects/{id}/tickets (ticket-210). */
export interface TicketListResponse {
  tickets: Ticket[];
  unreadable: TicketUnreadable[];
}

export interface PRStatus {
  state: "open" | "closed" | "merged";
  ci_status: "pending" | "passing" | "failing" | "none" | "unreadable";
  pr_url: string;
  pr_number: number;
}

/** One entry from GET /projects/{id}/pr-statuses (ticket-367). */
export interface PRStatusEntry extends PRStatus {
  ticket_id: string;
}

export interface TicketCreate {
  title: string;
  type?: TicketType;
  priority?: TicketPriority;
  description?: string;
  depends_on?: string[];
}

/** Corps de `POST /signalements` (ticket-407) : un défaut ou une idée sur Tessera. */
export type SignalementNature = "bug" | "idee";

export interface SignalementPayload {
  projet: string;
  nature: SignalementNature;
  titre: string;
  description: string;
  contexte?: string;
}

export interface TicketDraft {
  title: string;
  type: string;
  priority: string;
  agent: string;
  description: string;
  acceptance_criteria: string[];
  depends_on_index: number[];
}

export interface PlanResult {
  drafts: TicketDraft[];
  summary: string;
}

export interface TicketBatchResponse {
  created: Ticket[];
}

// ------------------------------------------------- suivi par ticket --------
// ticket-064 — ce qu'un ticket a produit, rassemblé en un endroit.

export interface TicketRunSummary {
  id: string;
  started_at: string;
  finished_at: string | null;
  rounds: number | null;
  approved: boolean | null;
  final_status: string | null;
  total_cost_usd: number;
  /** La cause d'un blocage, quand il y en a eu une (ticket-218). */
  arret?: string | null;
}

export interface TicketActivity {
  ticket_id: string;
  runs: TicketRunSummary[];
  pr_number: number | null;
  github_remote: string | null;
  /** L'IDE sait-il ouvrir une PR sur ce dépôt ? Faux hors GitHub (ticket-081). */
  pr_supported?: boolean;
  /** Le nom de l'hébergeur, pour le dire à l'utilisateur. */
  forge?: string | null;
  /**
   * Jusqu'où ce projet laisse l'IDE aller seul (ticket-082). Sans l'afficher,
   * rien n'explique pourquoi l'IDE s'arrête après le commit ici et va jusqu'au
   * merge ailleurs.
   */
  autonomy?: "commit" | "pr" | "merge";
}

export interface MergeResponse {
  pr_number: number;
  merged: boolean;
}

export interface OpenPrResponse {
  pr_number: number;
  pr_url: string;
  branch: string;
}

/** Ce qu'un run a produit, tel que le dépôt le montre (ticket-069). */
export interface TicketDiff {
  ticket_id: string;
  branch: string | null;
  /**
   * Le commit retrouvé quand la branche n'existe plus (ticket-116).
   * Supprimer la branche après le merge est la pratique normale : sans ce
   * repli, le diff disparaissait pour tout ticket proprement terminé.
   */
  commit: string | null;
  diff: string;
  files: string[];
}

/** Ce que le nettoyage peut retirer, et pourquoi le reste demeure (ticket-070). */
export interface PlanDeNettoyage {
  nettoyables: string[];
  /** [branche, raison] — la raison est destinée à être lue. */
  conservees: [string, string][];
}
