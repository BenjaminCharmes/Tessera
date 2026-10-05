import type {
  AgentDetail,
  ProjectAgents,
  AgentSettingsPatch,
  Limites,
  PipelineReglages,
  PipelineReglagesPatch,
  StatsPeriod,
  UsageStats,
  AgentInfo,
  AnalysisResult,
  CloneProjectRequest,
  CloneProjectResponse,
  ArtifactMode,
  ArtifactModeState,
  ChatHistory,
  ConversationSummary,
  GitStatus,
  RemovalPlan,
  ConversationMessage,
  CreateAgentResponse,
  ImportProjectRequest,
  ImportProjectResponse,
  PRStatus,
  RunRequest,
  RunEvent,
  ServiceActif,
  ProjectCreationResult,
  PipelineRun,
  PlanResult,
  MergeResponse,
  OpenPrResponse,
  Project,
  ProjectUsage,
  RecentRun,
  RunFromChatResponse,
  Ticket,
  TicketListResponse,
  TicketRunSummary,
  TicketStatus,
  TicketActivity,
  TicketDiff,
  PlanDeNettoyage,
  TicketBatchResponse,
  TicketCreate,
  TicketDraft,
} from "../types/api";
import { authorized } from "./auth";
import { API_ORIGIN } from "./config";

const BASE = `${API_ORIGIN}/api/v1`;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, authorized(options));
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function put<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function patch_<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

async function del(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, authorized({ method: "DELETE" }));
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
}

export const api = {
  projects: {
    list: (): Promise<Project[]> => request("/projects"),
    create: (
      name: string,
      description: string,
    ): Promise<ProjectCreationResult> =>
      post("/projects", {
        project_id: name.toLowerCase().replace(/\s+/g, "-"),
        name,
        description,
      }),
    import: (req: ImportProjectRequest): Promise<ImportProjectResponse> =>
      post("/projects/import", req),
    clone: (req: CloneProjectRequest): Promise<CloneProjectResponse> =>
      post("/projects/clone", req),
    analyze: (projectId: string, overwrite = false): Promise<AnalysisResult> =>
      post(`/projects/${projectId}/analyze`, { overwrite }),
    plan: (projectId: string, description: string): Promise<PlanResult> =>
      post(`/projects/${projectId}/plan`, { description }),
  },
  tickets: {
    activity: (projectId: string, ticketId: string): Promise<TicketActivity> =>
      request(`/projects/${projectId}/tickets/${ticketId}/activity`),
    diff: (projectId: string, ticketId: string): Promise<TicketDiff> =>
      request(`/projects/${projectId}/tickets/${ticketId}/diff`),
    openPr: (
      projectId: string,
      ticketId: string,
      branch: string,
    ): Promise<OpenPrResponse> =>
      post(`/projects/${projectId}/tickets/${ticketId}/open-pr`, { branch }),
    mergePr: (projectId: string, ticketId: string): Promise<MergeResponse> =>
      post(`/projects/${projectId}/tickets/${ticketId}/merge-pr`, {}),
    list: (projectId: string): Promise<TicketListResponse> =>
      request(`/projects/${projectId}/tickets`),
    /** Un statut posé à la main (ticket-194) ; le backend déplace le fichier et publie l'événement. */
    setStatus: (
      ticketId: string,
      status: TicketStatus,
      projectId: string,
    ): Promise<Ticket> =>
      patch_(`/projects/${projectId}/tickets/${ticketId}`, { status }),
    create: (projectId: string, data: TicketCreate): Promise<Ticket> =>
      post(`/projects/${projectId}/tickets`, data),
    batch: (
      projectId: string,
      tickets: TicketDraft[],
    ): Promise<TicketBatchResponse> =>
      post(`/projects/${projectId}/tickets/batch`, { tickets }),
    /** Les runs d'un ticket, du plus récent au plus ancien — ticket-327. */
    runs: (projectId: string, ticketId: string): Promise<TicketRunSummary[]> =>
      request(`/projects/${projectId}/tickets/${ticketId}/runs`),
  },
  orchestrator: {
    /**
     * Demarre un run et rend son identifiant, sans attendre la fin
     * (ticket-128). Le deroule s'observe sur `/orchestrator/observe`, ou
     * tous les runs de la machine passent.
     */
    run: (body: RunRequest): Promise<{ run_id: string }> =>
      request("/orchestrator/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
    /** Les plafonds de dépense, pour situer un coût (ticket-197). */
    limits: (): Promise<Limites> => request("/orchestrator/limits"),
  },
  services: {
    /**
     * Les services d'un projet — ticket-137. Rien de declare dans son
     * `agents.json`, et `start` repond 409 en disant quoi ecrire.
     */
    list: (projectId: string): Promise<ServiceActif[]> =>
      request(`/projects/${projectId}/services`),
    start: (projectId: string): Promise<{ services: ServiceActif[] }> =>
      post(`/projects/${projectId}/services/start`, {}),
    stop: (projectId: string): Promise<{ arretes: number }> =>
      post(`/projects/${projectId}/services/stop`, {}),
  },
  runs: {
    list: (projectId: string, limit = 20): Promise<PipelineRun[]> =>
      request(`/projects/${projectId}/runs?limit=${limit}`),
    /** Les événements d'un run terminé, pour rejouer la vue (ticket-280). */
    events: (runId: string): Promise<RunEvent[]> =>
      request(`/runs/${runId}/events`),
  },
  usage: {
    get: (projectId: string): Promise<ProjectUsage> =>
      request(`/projects/${projectId}/usage`),
    stats: (days: StatsPeriod, projectId: string | null): Promise<UsageStats> =>
      request(
        `/usage/stats?days=${days}` +
          (projectId ? `&project_id=${encodeURIComponent(projectId)}` : ""),
      ),
    /** Plus de runs récents, ou ceux qu'une recherche retient — ticket-335. */
    recentRuns: (
      days: StatsPeriod,
      projectId: string | null,
      limit: number,
      recherche: string,
    ): Promise<RecentRun[]> =>
      request(
        `/usage/recent-runs?days=${days}&limit=${limit}` +
          (projectId ? `&project_id=${encodeURIComponent(projectId)}` : "") +
          (recherche ? `&q=${encodeURIComponent(recherche)}` : ""),
      ),
  },
  github: {
    getPrStatus: (projectId: string, ticketId: string): Promise<PRStatus> =>
      request(`/projects/${projectId}/tickets/${ticketId}/pr-status`),
  },
  pipeline: {
    /** Les réglages du pipeline d'un projet (ticket-196). */
    get: (projectId: string): Promise<PipelineReglages> =>
      request(`/projects/${projectId}/pipeline`),
    set: (projectId: string, patch: PipelineReglagesPatch): Promise<PipelineReglages> =>
      patch_(`/projects/${projectId}/pipeline`, patch),
  },
  git: {
    status: (projectId: string): Promise<GitStatus> =>
      request(`/projects/${projectId}/git/status`),
    init: (projectId: string): Promise<GitStatus> =>
      post(`/projects/${projectId}/git/init`, {}),
    link: (
      projectId: string,
      repoUrl: string,
      confirmed = false,
    ): Promise<GitStatus> =>
      post(`/projects/${projectId}/git/link`, {
        repo_url: repoUrl,
        confirmed,
      }),
    removalPlan: (projectId: string): Promise<RemovalPlan> =>
      request(`/projects/${projectId}/removal-plan`),
    detach: (projectId: string): Promise<{ detached: boolean; moved_to: string }> =>
      post(`/projects/${projectId}/detach`, {}),
    remove: (projectId: string): Promise<void> =>
      del(`/projects/${projectId}?confirmed=true`),
    agents: (projectId: string): Promise<ProjectAgents> =>
      request(`/projects/${projectId}/agents`),
    setAgentModel: (
      projectId: string,
      role: string,
      patch: AgentSettingsPatch,
    ): Promise<ProjectAgents> =>
      put(`/projects/${projectId}/agents/${role}`, patch),
    cleanupPlan: (projectId: string): Promise<PlanDeNettoyage> =>
      request(`/projects/${projectId}/branches/cleanup`),
    cleanup: (projectId: string, branches: string[]): Promise<string[]> =>
      request(`/projects/${projectId}/branches/cleanup`, {
        method: "POST",
        body: JSON.stringify({ branches }),
      }),
    artifacts: (projectId: string): Promise<ArtifactModeState> =>
      request(`/projects/${projectId}/artifacts`),
    setArtifacts: (
      projectId: string,
      mode: ArtifactMode,
    ): Promise<ArtifactModeState> =>
      put(`/projects/${projectId}/artifacts`, { mode }),
  },
  chat: {
    list: (projectId: string): Promise<ConversationSummary[]> =>
      request(`/projects/${projectId}/chat`),
    history: (
      projectId: string,
      conversationId: string,
    ): Promise<ChatHistory> =>
      request(`/projects/${projectId}/chat/${conversationId}`),
    runPipeline: (
      projectId: string,
      conversationId: string,
      ticketId: string,
    ): Promise<RunFromChatResponse> =>
      post(`/projects/${projectId}/chat/run`, {
        conversation_id: conversationId,
        ticket_id: ticketId,
      }),
  },
  agents: {
    list: (): Promise<AgentInfo[]> =>
      request<{ agents: AgentInfo[] }>("/agents/registry").then(
        (r) => r.agents,
      ),
    detail: (role: string): Promise<AgentDetail> =>
      request(`/agents/registry/${role}`),
    updatePrompt: (role: string, systemPrompt: string): Promise<AgentDetail> =>
      put(`/agents/registry/${role}`, { system_prompt: systemPrompt }),
    remove: (role: string): Promise<void> => del(`/agents/registry/${role}`),
    createConversational: (
      conversation: ConversationMessage[],
    ): Promise<CreateAgentResponse> =>
      post("/agents/create-agent", { conversation }),
  },
};
