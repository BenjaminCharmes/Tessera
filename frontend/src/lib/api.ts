import type {
  AgentDetail,
  ProjectAgents,
  VentilationDesCouts,
  AgentInfo,
  AnalysisResult,
  CloneProjectRequest,
  CloneProjectResponse,
  ArtifactMode,
  ArtifactModeState,
  ChatHistory,
  GitStatus,
  RemovalPlan,
  ConversationMessage,
  CreateAgentResponse,
  CreatePrResponse,
  ImportProjectRequest,
  ImportProjectResponse,
  PRStatus,
  RunRequest,
  ServiceActif,
  ProjectCreationResult,
  PipelineRun,
  PlanResult,
  MergeResponse,
  OpenPrResponse,
  Project,
  ProjectUsage,
  RunFromChatResponse,
  Ticket,
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
    list: (projectId: string): Promise<Ticket[]> =>
      request(`/projects/${projectId}/tickets`),
    create: (projectId: string, data: TicketCreate): Promise<Ticket> =>
      post(`/projects/${projectId}/tickets`, data),
    batch: (
      projectId: string,
      tickets: TicketDraft[],
    ): Promise<TicketBatchResponse> =>
      post(`/projects/${projectId}/tickets/batch`, { tickets }),
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
  },
  usage: {
    get: (projectId: string): Promise<ProjectUsage> =>
      request(`/projects/${projectId}/usage`),
    breakdown: (projectId: string): Promise<VentilationDesCouts> =>
      request(`/projects/${projectId}/usage/breakdown`),
    breakdownGlobal: (): Promise<VentilationDesCouts> =>
      request("/projects/usage/breakdown"),
  },
  github: {
    createPr: (
      projectId: string,
      ticketId: string,
      headBranch: string,
      base = "develop",
    ): Promise<CreatePrResponse> =>
      post(`/projects/${projectId}/tickets/${ticketId}/create-pr`, {
        head_branch: headBranch,
        base,
      }),
    getPrStatus: (projectId: string, ticketId: string): Promise<PRStatus> =>
      request(`/projects/${projectId}/tickets/${ticketId}/pr-status`),
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
      model: string,
    ): Promise<ProjectAgents> =>
      put(`/projects/${projectId}/agents/${role}`, { model }),
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
