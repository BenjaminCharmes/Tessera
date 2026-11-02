import type { MomentAgent } from "../design/AgentBadge";

export interface AgentInfo {
  role: string;
  description: string | null;
  is_builtin: boolean;
  prompt_preview: string;
  /** Quand cet agent parle : pendant un run, sur une action, ou jamais. */
  moment?: MomentAgent;
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

/** Un agent et sa définition complète — son prompt système (ticket-076). */
export interface AgentDetail {
  role: string;
  is_builtin: boolean;
  moment?: MomentAgent;
  system_prompt: string;
}

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

/** Un agent tel que ce projet le configure (ticket-080). */
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
