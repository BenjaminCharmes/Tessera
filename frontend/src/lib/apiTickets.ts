import type {
  MergeResponse,
  OpenPrResponse,
  PRStatus,
  PRStatusEntry,
  Ticket,
  TicketActivity,
  TicketBatchResponse,
  TicketCreate,
  TicketDiff,
  TicketDraft,
  TicketListResponse,
  TicketRunSummary,
  TicketStatus,
} from "../types/api";
import { patch_, post } from "./apiVerbes";
import { request } from "./http";

export const tickets = {
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
    drafts: TicketDraft[],
  ): Promise<TicketBatchResponse> =>
    post(`/projects/${projectId}/tickets/batch`, { tickets: drafts }),
  /** Les runs d'un ticket, du plus récent au plus ancien — ticket-327. */
  runs: (projectId: string, ticketId: string): Promise<TicketRunSummary[]> =>
    request(`/projects/${projectId}/tickets/${ticketId}/runs`),
};

export const github = {
  getPrStatus: (projectId: string, ticketId: string): Promise<PRStatus> =>
    request(`/projects/${projectId}/tickets/${ticketId}/pr-status`),
  /** Statut de toutes les PR d'un projet en un seul appel (ticket-367). */
  getPrStatuses: (projectId: string): Promise<PRStatusEntry[]> =>
    request<{ statuses: PRStatusEntry[] }>(`/projects/${projectId}/pr-statuses`).then((r) => r.statuses),
};
