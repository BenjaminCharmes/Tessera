import type {
  AgentInfo,
  AnalysisResult,
  CloneProjectRequest,
  CloneProjectResponse,
  ArtifactMode,
  ArtifactModeState,
  ChatHistory,
  GitStatus,
  ConversationMessage,
  CreateAgentResponse,
  CreatePrResponse,
  ImportProjectRequest,
  ImportProjectResponse,
  PRStatus,
  PipelineResult,
  ProjectCreationResult,
  PipelineRun,
  PlanResult,
  Project,
  ProjectUsage,
  RunFromChatResponse,
  Ticket,
  TicketBatchResponse,
  TicketCreate,
  TicketDraft,
} from "../types/api";

const BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
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
  const res = await fetch(`${BASE}${path}`, { method: "DELETE" });
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
    run: (projectId: string, ticketId: string): Promise<PipelineResult> =>
      request("/orchestrator/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, ticket_id: ticketId }),
      }),
  },
  runs: {
    list: (projectId: string, limit = 20): Promise<PipelineRun[]> =>
      request(`/projects/${projectId}/runs?limit=${limit}`),
  },
  usage: {
    get: (projectId: string): Promise<ProjectUsage> =>
      request(`/projects/${projectId}/usage`),
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
    remove: (role: string): Promise<void> => del(`/agents/registry/${role}`),
    createConversational: (
      conversation: ConversationMessage[],
    ): Promise<CreateAgentResponse> =>
      post("/agents/create-agent", { conversation }),
  },
};
