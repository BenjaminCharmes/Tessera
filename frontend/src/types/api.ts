export type TicketStatus =
  "todo" | "in-progress" | "in-review" | "done" | "blocked" | "cancelled";

// Doit rester aligné sur TicketType côté backend
// (backend/src/vibe_ide/models/ticket.py) : types Conventional Commits
// + `design`, propre à vibe-ide.
export type TicketType =
  | "feat"
  | "fix"
  | "chore"
  | "docs"
  | "refactor"
  | "test"
  | "design";
export type TicketPriority = "critical" | "high" | "medium" | "low";
export type AgentRole =
  | "orchestrateur"
  | "codeur"
  | "reviewer"
  | "architect"
  | "project-creator"
  | "github-sync";

// Doit rester aligné sur EventType côté backend
// (backend/src/vibe_ide/services/pipeline_events.py). L'union était restée à
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
  | "pipeline_done"
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

export interface CreatePrResponse {
  pr_number: number;
  pr_url: string;
}

export interface OrchestratorEvent {
  type: EventType;
  agent: AgentRole | null;
  ticket_id: string;
  data: Record<string, unknown>;
  timestamp: string;
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
}

/** ticket-062 — les artefacts vibe-ide partent dans le dépôt, ou restent locaux. */
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
  diff: string;
  files: string[];
}
