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
  body: string;
  project_id: string;
  file_path: string;
}

export interface OrchestratorEvent {
  type: EventType;
  agent: AgentRole | null;
  ticket_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

export interface PipelineResult {
  ticket_id: string;
  final_status: TicketStatus;
  rounds: number;
  approved: boolean;
}
