export type TicketStatus =
  | "todo"
  | "in-progress"
  | "in-review"
  | "done"
  | "blocked"
  | "cancelled";

export type TicketType = "feat" | "fix" | "chore" | "design" | "docs";
export type TicketPriority = "critical" | "high" | "medium" | "low";
export type AgentRole =
  | "orchestrateur"
  | "codeur"
  | "reviewer"
  | "architect"
  | "project-creator"
  | "github-sync";

export type EventType =
  | "agent_started"
  | "agent_token"
  | "agent_done"
  | "ticket_status_changed"
  | "pipeline_done"
  | "error";

export interface Project {
  id: string;
  name: string;
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
}

export interface PipelineRun {
  id: string;
  ticket_id: string;
  started_at: string;
  finished_at: string | null;
  rounds: number | null;
  approved: boolean | null;
  final_status: string | null;
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
