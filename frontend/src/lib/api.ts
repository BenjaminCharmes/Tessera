import type {
  PipelineResult,
  Project,
  Ticket,
  TicketCreate,
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

export const api = {
  projects: {
    list: (): Promise<Project[]> => request("/projects"),
    create: (name: string, description: string): Promise<Project> =>
      post("/projects", { name, description }),
  },
  tickets: {
    list: (projectId: string): Promise<Ticket[]> =>
      request(`/projects/${projectId}/tickets`),
    create: (projectId: string, data: TicketCreate): Promise<Ticket> =>
      post(`/projects/${projectId}/tickets`, data),
  },
  orchestrator: {
    run: (projectId: string, ticketId: string): Promise<PipelineResult> =>
      request("/orchestrator/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ project_id: projectId, ticket_id: ticketId }),
      }),
  },
};
