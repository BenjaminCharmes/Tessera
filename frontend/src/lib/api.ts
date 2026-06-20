import type { PipelineResult, Project, Ticket } from "../types/api";

const BASE = "/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  projects: {
    list: (): Promise<Project[]> => request("/projects"),
  },
  tickets: {
    list: (projectId: string): Promise<Ticket[]> =>
      request(`/projects/${projectId}/tickets`),
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
