import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { groupByStatus, EMPTY_BY_STATUS } from "../lib/ticketBoard";
import type { ByStatus } from "../lib/ticketBoard";
import type { OrchestratorEvent, Ticket, TicketStatus, TicketUnreadable } from "../types/api";
import { useFenetreVisible } from "./useFenetreVisible";

export type { ByStatus };

export interface UseTicketsResult {
  tickets: Ticket[];
  byStatus: ByStatus;
  /** Ticket files the backend could not parse (ticket-210). */
  unreadable: TicketUnreadable[];
  loading: boolean;
  error: string | null;
  refresh: () => void;
}

/**
 * Dernière liste chargée, avec ce qui l'a produite.
 *
 * L'état est **clé** par projet et révision plutôt que remis à zéro dans
 * l'effet : `loading`, `error` et la liste vide d'un projet absent se
 * déduisent en comparant la clé courante à celle du chargement, sans aucun
 * `setState` synchrone dans un effet (ticket-123).
 */
interface Chargement {
  projectId: string;
  revision: number;
  tickets: Ticket[];
  unreadable: TicketUnreadable[];
  error: string | null;
}

const AUCUN: Ticket[] = [];
const AUCUN_ILLISIBLE: TicketUnreadable[] = [];

export function useTickets(
  projectId: string | null,
  isPipelineActive: boolean = false,
  events: OrchestratorEvent[] = [],
): UseTicketsResult {
  const [charge, setCharge] = useState<Chargement | null>(null);
  const [revision, setRevision] = useState(0);
  const processedEventsRef = useRef(0);
  const fenetreVisible = useFenetreVisible();
  // Permet de détecter la transition cachée → visible sans relancer au montage.
  const prevFenetreVisibleRef = useRef<boolean | null>(null);

  const memeProjet = charge !== null && charge.projectId === projectId;
  const aJour = memeProjet && charge.revision === revision;

  useEffect(() => {
    if (!projectId) {
      processedEventsRef.current = 0;
      return;
    }
    let cancelled = false;
    api.tickets
      .list(projectId)
      .then((data) => {
        if (cancelled) return;
        processedEventsRef.current = events.length;
        setCharge({
          projectId,
          revision,
          tickets: data.tickets,
          unreadable: data.unreadable,
          error: null,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setCharge((prev) => ({
          projectId,
          revision,
          tickets:
            prev && prev.projectId === projectId ? prev.tickets : AUCUN,
          unreadable:
            prev && prev.projectId === projectId ? prev.unreadable : AUCUN_ILLISIBLE,
          error: err instanceof Error ? err.message : "Unknown error",
        }));
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, revision]);

  // Polling fallback — suspendu quand la fenêtre est cachée (ticket-356).
  useEffect(() => {
    if (!projectId || !fenetreVisible) return;
    const delay = isPipelineActive ? 30_000 : 60_000;
    const timer = setInterval(() => setRevision((r) => r + 1), delay);
    return () => clearInterval(timer);
  }, [projectId, isPipelineActive, fenetreVisible]);

  // Relance immédiate au retour en premier plan (ticket-356).
  useEffect(() => {
    if (!projectId) return;
    if (prevFenetreVisibleRef.current === false && fenetreVisible) {
      setRevision((r) => r + 1);
    }
    prevFenetreVisibleRef.current = fenetreVisible;
  }, [fenetreVisible, projectId]);

  // React to real-time WS events
  useEffect(() => {
    // Le flux repart de zéro à chaque `clear()` ou nouveau run : un compte
    // resté à l'ancienne longueur faisait ignorer les premiers événements du
    // run suivant (ticket-123).
    if (events.length < processedEventsRef.current) {
      processedEventsRef.current = events.length;
    }
    const newEvents = events.slice(processedEventsRef.current);
    if (newEvents.length === 0) return;
    processedEventsRef.current = events.length;

    for (const event of newEvents) {
      if (
        event.type === "ticket_status_changed" &&
        typeof event.data["status"] === "string"
      ) {
        const newStatus = event.data["status"] as TicketStatus;
        setCharge((prev) =>
          prev === null
            ? prev
            : {
                ...prev,
                tickets: prev.tickets.map((t) =>
                  t.id === event.ticket_id ? { ...t, status: newStatus } : t,
                ),
              },
        );
      }
    }
  }, [events]);

  const tickets = memeProjet ? charge.tickets : AUCUN;
  const unreadable = memeProjet ? charge.unreadable : AUCUN_ILLISIBLE;
  const byStatus = tickets.length ? groupByStatus(tickets) : EMPTY_BY_STATUS;

  return {
    tickets,
    byStatus,
    unreadable,
    loading: projectId !== null && !aJour,
    error: aJour ? charge.error : null,
    refresh: () => setRevision((r) => r + 1),
  };
}
