import type { MomentAgent } from "../design/AgentBadge";

export type TicketStatus =
  "todo" | "in-progress" | "in-review" | "done" | "blocked" | "cancelled";

// Doit rester aligné sur TicketType côté backend
// (backend/src/tessera/models/ticket.py) : types Conventional Commits
// + `design`, propre à Tessera.
export type TicketType =
  "feat" | "fix" | "chore" | "docs" | "refactor" | "test" | "design";
export type TicketPriority = "critical" | "high" | "medium" | "low";
export type AgentRole =
  | "orchestrateur"
  | "codeur"
  | "reviewer"
  | "architect"
  | "project-creator"
  | "github-sync";

// Doit rester aligné sur EventType côté backend
// (backend/src/tessera/services/pipeline_events.py). L'union était restée à
// six valeurs alors que le pipeline en émet quatorze : les événements
// manquants traversaient l'UI sans type, donc sans traitement possible.
export type EventType =
  | "agent_started"
  | "agent_token"
  | "agent_tool_use"
  | "agent_done"
  | "agent_question"
  | "branch_created"
  | "ticket_status_changed"
  | "test_result"
  | "security_audit_started"
  | "security_audit_done"
  | "validation_done"
  | "doc_updated"
  | "commit_created"
  | "quota_updated"
  | "provider_fallback"
  | "queue_progress"
  | "livraison_done"
  | "pipeline_done"
  | "run_closed"
  | "service_output"
  | "service_closed"
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

export interface Project {
  id: string;
  name: string;
  /** Chemin absolu du projet sur le disque — sert à l'ouvrir dans VSCode. */
  path: string;
  description: string;
  active_agents: string[];
  stack: string | null;
  raw_claude_md: string;
  github_remote: string | null;
  /** Le rangement déclaré dans agents.json — null si le projet n'en déclare pas (ticket-175). */
  category?: string | null; /**
   * Ce projet execute l'IDE en ce moment (ticket-152). Lui proposer
   * « Lancer » demarrerait un second backend sur un port deja pris.
   */
  fait_tourner_l_ide?: boolean;
}

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

export interface PRStatus {
  state: "open" | "closed" | "merged";
  ci_status: "pending" | "passing" | "failing" | "none";
  pr_url: string;
  pr_number: number;
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
  mode?: "single" | "queue" | "autonomous";
  max_tickets?: number;
  depuis_github?: boolean;
}

/** Un service lance pour un projet (ticket-137). */
export interface ServiceActif {
  nom: string;
  project_id: string;
  /** `null` pour un service declare mais pas lance (ticket-146). */
  pid: number | null;
  demarre_a: string;
  en_cours: boolean;
  code_de_sortie: number | null;
  /**
   * Les dernieres lignes que le service a ecrites, gardees par le backend
   * (ticket-148). Le canal ne rejoue pas l'historique : sans elles, qui ouvre
   * l'IDE apres le demarrage ne verrait jamais l'adresse annoncee.
   */
  sortie?: string[];
  /**
   * Vrai quand c'est l'utilisateur qui a demande l'arret (ticket-151).
   * `terminate()` laisse un code non nul sur certaines plateformes : sans ce
   * drapeau, un service qu'on vient d'arreter s'afficherait en echec.
   */
  arrete_a_la_main?: boolean;
}

/** L'instantane des runs vivants, envoye a la connexion sur `/observe`. */
export interface RunActif {
  run_id: string;
  project_id: string;
  mode: string;
  ticket_id: string | null;
  etape: string | null;
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
  demarre_a: string;
}

export interface TicketCreate {
  title: string;
  type?: TicketType;
  priority?: TicketPriority;
  description?: string;
  depends_on?: string[];
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
}

export interface TicketUsage {
  ticket_id: string;
  total_cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  call_count: number;
}

export interface ProjectUsage {
  total_cost_usd: number;
  total_tokens: number;
  total_runs: number;
  per_ticket: TicketUsage[];
}

export interface AgentInfo {
  role: string;
  description: string | null;
  is_builtin: boolean;
  prompt_preview: string;
  /** Quand cet agent parle : pendant un run, sur une action, ou jamais. */
  moment?: MomentAgent;
}

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

export interface AgentCreatedInfo {
  role: string;
  description: string | null;
}

export interface CreateAgentResponse {
  agent: AgentCreatedInfo | null;
  message: string;
  created: boolean;
}

export interface ProjectCreationResult {
  project: Project;
  agents_created: string[];
  /**
   * Le projet est-il la racine d'un dépôt git utilisable (ticket-104) ?
   * Faux si l'initialisation a échoué : le projet existe alors sur disque,
   * mais aucun run n'y démarrera tant qu'on n'aura pas rattrapé à la main.
   */
  repository_ready: boolean;
}

export interface ImportProjectRequest {
  source_path: string;
  mode: "copy" | "symlink";
  project_id?: string;
}

export interface ImportProjectResponse {
  project: Project;
}

export interface AnalysisResult {
  claude_md: string;
  detected_stack: string[];
  suggested_agents: string[];
  claude_md_written: boolean;
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

export interface CloneProjectRequest {
  repo_url: string;
  project_id?: string;
}

export interface CloneProjectResponse {
  project: Project;
  claude_md_generated: boolean;
  detected_stack: string[];
}

// ---------------------------------------------------------------- chat ----
// ticket-048 — chat conversationnel avec outils.

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  cost_usd: number;
  ts: string;
}

export interface ChatHistory {
  project_id: string;
  conversation_id: string;
  messages: ChatMessage[];
  spent_usd: number;
  max_usd: number;
}

/** Résultat d'un pipeline lancé depuis la conversation (ticket-055). */
export interface RunFromChatResponse {
  ticket_id: string;
  approved: boolean;
  rounds: number;
  final_status: string;
  branch: string | null;
  commit_sha: string | null;
}

/** Appel d'outil rendu dans le fil, replié par défaut. */
export interface ChatToolUse {
  tool: string;
  input: Record<string, unknown>;
}

// ---------------------------------------------------------- liaison git ----
// ticket-061 — un projet créé de zéro ou importé en `copy` n'a aucun dépôt.

export interface GitStatus {
  is_repository: boolean;
  has_commits: boolean;
  remote_url: string | null;
  /** Renseigné quand le projet vit dans un dépôt qui n'est pas le sien. */
  nested_in: string | null;
  /** Le projet déclare `git_root: ancestor` et travaille dans le dépôt qui le
   *  contient — ce n'est pas une anomalie à corriger (ticket-171). */
  uses_parent_repository: boolean;
}

/** ticket-062 — les artefacts Tessera partent dans le dépôt, ou restent locaux. */
export type ArtifactMode = "tracked" | "local";

export interface ArtifactModeState {
  mode: ArtifactMode;
  /** Artefacts déjà dans l'index git : l'exclusion ne les en sort pas. */
  already_tracked: string[];
}

/** ticket-063 — ce qu'un retrait toucherait, à montrer avant de décider. */
export interface RemovalPlan {
  project_id: string;
  /** Chemin réellement visé, liens résolus. */
  real_path: string;
  is_symlink: boolean;
  unpushed_commits: number;
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

/** Un agent et sa définition complète — son prompt système (ticket-076). */
export interface AgentDetail {
  role: string;
  is_builtin: boolean;
  moment?: MomentAgent;
  system_prompt: string;
}

/** Les statistiques d'une période, jours UTC (ticket-201). */
export type StatsPeriod = 7 | 30 | 90;

export interface UsageTotals {
  runs: number;
  calls: number;
  input_tokens: number;
  output_tokens: number;
  cache_read_tokens: number;
  pipeline_cost_usd: number;
  chat_cost_usd: number;
  cost_usd: number;
  call_duration_ms: number;
}

export interface DailyPoint {
  day: string;
  runs: number;
  input_tokens: number;
  output_tokens: number;
  /** Chat compris. */
  cost_usd: number;
}

export interface BreakdownLine {
  key: string;
  cost_usd: number;
  tokens: number;
  calls: number;
  avg_duration_ms: number;
}

export interface RunQuality {
  finished_runs: number;
  approval_rate: number | null;
  avg_rounds: number | null;
  avg_run_duration_ms: number | null;
  by_status: { status: string; count: number }[];
}

export interface RecentRun {
  id: string;
  project_id: string;
  ticket_id: string;
  started_at: string;
  finished_at: string | null;
  approved: boolean | null;
  final_status: string | null;
  cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  duration_ms: number | null;
}

export interface UsageStats {
  days: StatsPeriod;
  project_id: string | null;
  since: string;
  until: string;
  totals: UsageTotals;
  daily: DailyPoint[];
  per_agent: BreakdownLine[];
  per_model: BreakdownLine[];
  per_project: BreakdownLine[];
  quality: RunQuality;
  recent_runs: RecentRun[];
}

/** Un agent tel que ce projet le configure (ticket-080). */
/** La configuration effective du pipeline d'un projet (ticket-196). */
export interface PipelineReglages {
  max_review_rounds: number;
  testeur_enabled: boolean;
  test_command: string | null;
  securite_enabled: boolean;
  validateur_enabled: boolean;
  autonomy: string;
  merge_without_ci: boolean;
}

export type PipelineReglagesPatch = Partial<PipelineReglages>;

/** Les plafonds de dépense du backend (ticket-197). 0 = aucune borne. */
export interface Limites {
  run_max_budget_usd: number;
  llm_max_budget_usd: number;
}

/** Sur quoi retomber quand le provider d'un rôle ne répond pas (ticket-188). */
export interface FallbackConfig {
  provider: string;
  model: string;
}

export interface ProjectAgentConfig {
  role: string;
  model: string;
  max_tokens: number;
  active: boolean;
  provider: string;
  fallback: FallbackConfig | null;
}

export interface ProjectAgents {
  agents: ProjectAgentConfig[];
  /** Les seuls modèles proposables sur un provider Anthropic : ceux dont l'app sait calculer le coût. */
  known_models: string[];
  /** Les providers qu'un rôle peut déclarer (ticket-188). */
  known_providers: string[];
  /** Par provider, la liste proposable — vide quand le nom est libre. */
  known_models_by_provider: Record<string, string[]>;
}

/** Ce qu'on change sur un agent d'un projet. `fallback` omis : le repli ne bouge pas ; `null` : retiré. */
export interface AgentSettingsPatch {
  model: string;
  provider?: string;
  fallback?: FallbackConfig | null;
}
