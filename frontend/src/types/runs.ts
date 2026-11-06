import type { TicketStatus } from "./tickets";

export type AgentRole = "orchestrateur" | "codeur" | "reviewer" | "architect" | "project-creator" | "github-sync";

// Aligné sur EventType côté backend (services/noyau/pipeline_events.py) : un test
// de `backend/tests` le vérifie dans les deux sens.
export type EventType =
  | "agent_started"
  | "agent_token"
  | "agent_tool_use"
  | "agent_done"
  | "agent_question"
  | "branch_created"
  | "ticket_status_changed"
  | "test_started"
  | "test_result"
  | "security_audit_started"
  | "security_audit_done"
  | "validation_done"
  | "doc_updated"
  | "commit_created"
  | "quota_updated"
  | "provider_fallback"
  | "security_audit_fallback"
  | "queue_progress"
  | "livraison_done"
  | "pipeline_done"
  | "run_closed"
  | "service_output"
  | "service_closed"
  | "documentation_failed"
  | "validation_started"
  | "documentation_started"
  | "livraison_started"
  | "ci_merge_done"
  | "answer_ack"
  | "provisioning_step"
  | "run_resumed_from_existing_work"
  | "worktree_setup"
  | "external_wait"
  | "conflict_resolution"
  | "visual_check"
  | "run_anomaly"
  | "superviseur_action"
  | "error";

/** État du quota d'abonnement, diffusé par l'événement `quota_updated`. */
export interface QuotaState {
  known: boolean;
  status?: "allowed" | "allowed_warning" | "rejected";
  utilization?: number;
  window?: string | null;
  resets_at?: string | null;
  run_interrupted?: boolean;
}

export interface OrchestratorEvent {
  type: EventType;
  agent: AgentRole | null;
  ticket_id: string;
  data: Record<string, unknown>;
  timestamp: string;
  /**
   * De quel run vient l'evenement, et sur quel projet (ticket-128). Le canal
   * d'observation porte tous les runs de la machine : sans ces deux champs,
   * un client ne saurait pas a quoi rattacher ce qu'il recoit.
   */
  run_id?: string | null;
  project_id?: string | null;
}

/** Ce que `POST /orchestrator/run` accepte — les trois modes (ticket-128). */
export interface RunRequest {
  project_id: string;
  ticket_id?: string | null;
  ticket_ids?: string[];
  mode?: "single" | "queue" | "autonomous" | "revue";
  max_tickets?: number;
  depuis_github?: boolean;
}

/** La réponse de `POST /orchestrator/run` ; une revue y ajoute sa fiche et son coût (ticket-864). */
export interface RunDemarre {
  run_id: string;
  ticket_id?: string | null;
  plafond_usd?: number | null;
  cout_estime_usd?: number | null;
}

/** L'instantane des runs vivants, envoye a la connexion sur `/observe`. */
/** Les six règles du détecteur d'anomalies (ADR-078, ticket-834). */
export type RegleAnomalie =
  | "outil_repete"
  | "etape_longue"
  | "silence"
  | "cout_anormal"
  | "tours_de_revue"
  | "blocages_identiques";

/** Une anomalie relevée sur un run, telle que `run_anomaly` la porte. Jamais l'`input` d'un outil. */
export interface Anomalie {
  /** Une règle que ce client ne connaît pas se rend avec son identifiant brut. */
  regle: RegleAnomalie | (string & {});
  /** Clé de dédoublonnage : un épisode, pas une règle. */
  cle: string;
  ticket_id: string;
  message: string;
  mesure: number;
  seuil: number;
  unite: "appels" | "s" | "usd" | "pourcent" | "tours" | "runs";
  etape?: string | null;
  agent?: string | null;
}

export interface RunActif {
  run_id: string;
  project_id: string;
  mode: string;
  ticket_id: string | null;
  /** Titre lisible du ticket en cours (ticket-286). Absent sur un backend ancien. */
  ticket_titre?: string | null;
  /**
   * Identifiant en base du run (ticket-325). Présent dès que la ligne existe
   * en base ; absent sur un backend plus ancien. Permet au frontend de charger
   * les événements persistés via GET /runs/{db_run_id}/events au rechargement
   * de page, pour reconstruire toutes les cartes du fil chronologique.
   */
  db_run_id?: string | null;
  etape: string | null;
  /** Étapes actives en parallèle — livré par ticket-289. Absent sur un backend ancien. */
  etapes_en_cours?: string[] | null;
  agent: AgentRole | null;
  tour: number;
  tokens_entree: number;
  tokens_sortie: number;
  cout_usd: number;
  /** Appels d'agent finis, et appels d'outils de l'agent en cours (ticket-197). */
  appels?: number;
  outils?: number;
  verdict: string | null;
  /** La question qu'un agent attend de voir répondue (ticket-163). */
  question?: string | null;
  /** Quand l'agent repartira seul sur une hypothèse énoncée (ticket-186). */
  question_expire_a?: string | null;
  /** Où en est la file, et ce qu'il lui reste — vides hors file (ticket-172).
   *  Optionnels : ils viennent du réseau, et un backend plus ancien ne les
   *  envoie pas. Les lire défensivement vaut mieux qu'une carte qui disparaît. */
  file_index?: number;
  file_total?: number;
  file_restants?: string[];
  /** Les tickets que la file a déjà traités (ticket-179). */
  file_faits?: string[];
  /** Les anomalies que le détecteur a relevées, 20 au plus (ADR-078). Absent sur un backend ancien. */
  anomalies?: Anomalie[];
  demarre_a: string;
}

export interface PipelineResult {
  ticket_id: string;
  final_status: TicketStatus;
  rounds: number;
  approved: boolean;
  /** Branche du run et commit produit — absents tant que le run n'a rien commité. */
  branch?: string | null;
  commit_sha?: string | null;
}

export interface PipelineRun {
  id: string;
  ticket_id: string;
  started_at: string;
  finished_at: string | null;
  rounds: number | null;
  approved: boolean | null;
  final_status: string | null;
  total_cost_usd: number;
  /** La cause d'un blocage, quand il y en a eu une (ticket-218). */
  arret?: string | null;
  /** Le run de la file qui porte ce run de ticket, absent pour un run seul. */
  parent_run_id?: string | null;
}

/** Un événement d'un run terminé, renvoyé par GET /runs/{id}/events (ticket-280). */
export interface RunEvent {
  type: EventType;
  agent: string | null;
  data: Record<string, unknown>;
  timestamp: string;
}

/** Ce qu'un ajout à une file a fait — `POST /orchestrator/runs/{id}/append`. */
export interface AjoutALaFile {
  ajoutes: string[];
  ignores: Record<string, string>;
  refuses: Record<string, string>;
}
