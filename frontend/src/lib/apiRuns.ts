import type {
  AjoutALaFile,
  Limites,
  PipelineRun,
  ProjectUsage,
  RecentRun,
  RunEvent,
  RunRequest,
  StatsPeriod,
  UsageStats,
} from "../types/api";
import { post } from "./apiVerbes";
import { request } from "./http";

export const orchestrator = {
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
  /**
   * Ajoute des tickets au bout d'une file qui tourne (ticket-478) ; 409 si
   * le run n'est pas une file ouverte. Un ticket déjà dans la file est ignoré.
   */
  append: (runId: string, ticketIds: string[]): Promise<AjoutALaFile> =>
    post(`/orchestrator/runs/${runId}/append`, { ticket_ids: ticketIds }),
  /** Les plafonds de dépense, pour situer un coût (ticket-197). */
  limits: (): Promise<Limites> => request("/orchestrator/limits"),
};

export const runs = {
  list: (projectId: string, limit = 20): Promise<PipelineRun[]> =>
    request(`/projects/${encodeURIComponent(projectId)}/runs?limit=${limit}`),
  /** Les événements d'un run terminé, pour rejouer la vue (ticket-280). */
  events: (runId: string): Promise<RunEvent[]> =>
    request(`/runs/${runId}/events`),
};

export const usage = {
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
};
