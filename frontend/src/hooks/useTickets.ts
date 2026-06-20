import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Ticket, TicketStatus } from "../types/api";

type ByStatus = Record<TicketStatus, Ticket[]>;

export interface UseTicketsResult {
  tickets: Ticket[];
  byStatus: ByStatus;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

const EMPTY_BY_STATUS: ByStatus = {
  todo: [],
  "in-progress": [],
  "in-review": [],
  done: [],
  blocked: [],
  cancelled: [],
};

function groupByStatus(tickets: Ticket[]): ByStatus {
  const result: ByStatus = {
    todo: [],
    "in-progress": [],
    "in-review": [],
    done: [],
    blocked: [],
    cancelled: [],
  };
  for (const ticket of tickets) {
    result[ticket.status].push(ticket);
  }
  return result;
}

export function useTickets(
  projectId: string | null,
  isPipelineActive: boolean = false,
): UseTicketsResult {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => {
    if (!projectId) {
      setTickets([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.tickets
      .list(projectId)
      .then((data) => {
        if (!cancelled) setTickets(data);
      })
      .catch((err: unknown) => {
        if (!cancelled)
          setError(err instanceof Error ? err.message : "Unknown error");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, revision]);

  useEffect(() => {
    if (!projectId) return;
    const delay = isPipelineActive ? 5_000 : 30_000;
    const timer = setInterval(() => setRevision((r) => r + 1), delay);
    return () => clearInterval(timer);
  }, [projectId, isPipelineActive]);

  return {
    tickets,
    byStatus: tickets.length ? groupByStatus(tickets) : EMPTY_BY_STATUS,
    loading,
    error,
    refresh: () => setRevision((r) => r + 1),
  };
}
