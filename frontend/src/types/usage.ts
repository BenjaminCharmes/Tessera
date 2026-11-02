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
