import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { groupByStatus, moveTicket, EMPTY_BY_STATUS } from "../lib/ticketBoard";
import type { ByStatus } from "../lib/ticketBoard";
import type { OrchestratorEvent, Ticket, TicketStatus } from "../types/api";

export type { ByStatus };

export interface UseTicketsResult {
  tickets: Ticket[];
  byStatus: ByStatus;
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

export function useTickets(
  projectId: string | null,
  isPipelineActive: boolean = false,
  events: OrchestratorEvent[] = [],
): UseTicketsResult {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);
  const processedEventsRef = useRef(0);

  useEffect(() => {
    if (!projectId) {
      setTickets([]);
      processedEventsRef.current = 0;
      return;
    }
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.tickets
      .list(projectId)
      .then((data) => {
        if (!cancelled) {
          setTickets(data);
          processedEventsRef.current = events.length;
        }
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, revision]);

  // Polling fallback (slower when pipeline active)
  useEffect(() => {
    if (!projectId) return;
    const delay = isPipelineActive ? 30_000 : 60_000;
    const timer = setInterval(() => setRevision((r) => r + 1), delay);
    return () => clearInterval(timer);
  }, [projectId, isPipelineActive]);

  // React to real-time WS events
  useEffect(() => {
    const newEvents = events.slice(processedEventsRef.current);
    if (newEvents.length === 0) return;
    processedEventsRef.current = events.length;

    for (const event of newEvents) {
      if (
        event.type === "ticket_status_changed" &&
        typeof event.data["status"] === "string"
      ) {
        const newStatus = event.data["status"] as TicketStatus;
        setTickets((prev) =>
          prev.map((t) =>
            t.id === event.ticket_id ? { ...t, status: newStatus } : t,
          ),
        );
      }
    }
  }, [events]);

  const byStatus = tickets.length ? groupByStatus(tickets) : EMPTY_BY_STATUS;

  return {
    tickets,
    byStatus,
    loading,
    error,
    refresh: () => setRevision((r) => r + 1),
  };
}
