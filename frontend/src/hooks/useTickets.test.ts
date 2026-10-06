import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useTickets } from "./useTickets";
import * as apiModule from "../lib/api";
import type { OrchestratorEvent, Ticket, TicketListResponse } from "../types/api";

function setVisibility(state: "visible" | "hidden"): void {
  Object.defineProperty(document, "visibilityState", {
    value: state,
    configurable: true,
  });
}

const TICKET_TODO: Ticket = {
  id: "ticket-001",
  title: "A todo ticket",
  type: "feat",
  status: "todo",
  priority: "medium",
  agent: "codeur",
  depends_on: [],
  created: "2026-06-20",
  github_issue_url: null,
  pr_number: null,
  body: "",
  project_id: "proj-1",
  file_path: "/tmp/ticket-001.md",
};

const TICKET_DONE: Ticket = {
  ...TICKET_TODO,
  id: "ticket-002",
  title: "A done ticket",
  status: "done",
};

vi.mock("../lib/api", () => ({
  api: {
    tickets: {
      list: vi.fn(),
    },
  },
}));

function makeEvent(
  type: OrchestratorEvent["type"],
  data: Record<string, unknown>,
  ticketId = "ticket-001",
): OrchestratorEvent {
  return {
    type,
    ticket_id: ticketId,
    agent: "codeur",
    data,
  } as OrchestratorEvent;
}

describe("useTickets", () => {
  const DEFAULT_RESPONSE: TicketListResponse = {
    tickets: [TICKET_TODO, TICKET_DONE],
    unreadable: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
    setVisibility("visible");
    vi.mocked(apiModule.api.tickets.list).mockResolvedValue(DEFAULT_RESPONSE);
  });

  afterEach(() => {
    setVisibility("visible");
  });

  it("fetches tickets on mount", async () => {
    const { result } = renderHook(() => useTickets("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.tickets).toHaveLength(2);
  });

  it("groups tickets by status", async () => {
    const { result } = renderHook(() => useTickets("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.byStatus.todo).toHaveLength(1);
    expect(result.current.byStatus.done).toHaveLength(1);
  });

  it("returns empty state when projectId is null", () => {
    const { result } = renderHook(() => useTickets(null));
    expect(result.current.tickets).toHaveLength(0);
    expect(result.current.loading).toBe(false);
  });

  it("applies ticket_status_changed event in real time", async () => {
    const { result, rerender } = renderHook(
      ({ events }: { events: OrchestratorEvent[] }) =>
        useTickets("proj-1", false, events),
      { initialProps: { events: [] as OrchestratorEvent[] } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(
      result.current.tickets.find((t) => t.id === "ticket-001")?.status,
    ).toBe("todo");

    const event = makeEvent("ticket_status_changed", { status: "in-progress" });

    act(() => {
      rerender({ events: [event] });
    });

    expect(
      result.current.tickets.find((t) => t.id === "ticket-001")?.status,
    ).toBe("in-progress");
  });

  it("does not re-process already-handled events", async () => {
    const event = makeEvent("ticket_status_changed", { status: "in-review" });

    const { result, rerender } = renderHook(
      ({ events }: { events: OrchestratorEvent[] }) =>
        useTickets("proj-1", false, events),
      { initialProps: { events: [] as OrchestratorEvent[] } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    // first rerender: apply the event
    act(() => {
      rerender({ events: [event] });
    });
    expect(
      result.current.tickets.find((t) => t.id === "ticket-001")?.status,
    ).toBe("in-review");

    // second rerender with same array: event must not be re-processed
    // (would reset to "in-review" again, which is the same, but list must not be re-fetched)
    act(() => {
      rerender({ events: [event] });
    });
    expect(
      result.current.tickets.find((t) => t.id === "ticket-001")?.status,
    ).toBe("in-review");
    // api.tickets.list called only once (initial load, not triggered by events)
    expect(apiModule.api.tickets.list).toHaveBeenCalledTimes(1);
  });

  it("traite un ticket_status_changed reçu après que le flux a été vidé (ticket-123)", async () => {
    // `processedEventsRef` n'était remis à jour que si de nouveaux événements
    // arrivaient : après `stream.clear()` (events = []), il gardait l'ancien
    // compte, et les premiers événements du run suivant étaient ignorés
    // parce que `events.slice(ancien)` rendait un tableau vide.
    const premier = makeEvent("ticket_status_changed", { status: "in-progress" });
    const second = makeEvent("ticket_status_changed", { status: "in-review" });

    const { result, rerender } = renderHook(
      ({ events }: { events: OrchestratorEvent[] }) =>
        useTickets("proj-1", false, events),
      { initialProps: { events: [] as OrchestratorEvent[] } },
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      rerender({ events: [premier, premier, premier] });
    });
    expect(
      result.current.tickets.find((t) => t.id === "ticket-001")?.status,
    ).toBe("in-progress");

    // clear() : le flux repart de zéro.
    act(() => {
      rerender({ events: [] });
    });
    act(() => {
      rerender({ events: [second] });
    });

    expect(
      result.current.tickets.find((t) => t.id === "ticket-001")?.status,
    ).toBe("in-review");
  });

  it("ne fait aucune requête de polling fenêtre cachée, et relance au retour (ticket-356)", async () => {
    // Critère : le polling s'arrête quand personne ne regarde, et repart
    // dès que la fenêtre revient au premier plan.
    vi.useFakeTimers();
    try {
      renderHook(() =>
        useTickets("proj-1", true /* pipeline actif = intervalle 30 s */),
      );
      // Attendre le chargement initial.
      await vi.advanceTimersByTimeAsync(0);
      const apresInit = vi.mocked(apiModule.api.tickets.list).mock.calls.length;

      // Cacher la fenêtre.
      await act(async () => {
        setVisibility("hidden");
        document.dispatchEvent(new Event("visibilitychange"));
        await vi.advanceTimersByTimeAsync(0);
      });

      // Avancer bien au-delà de l'intervalle de 30 s : aucun appel supplémentaire.
      await vi.advanceTimersByTimeAsync(120_000);
      expect(vi.mocked(apiModule.api.tickets.list).mock.calls.length).toBe(
        apresInit,
      );

      // Rendre la fenêtre visible : une requête immédiate doit partir.
      await act(async () => {
        setVisibility("visible");
        document.dispatchEvent(new Event("visibilitychange"));
        await vi.advanceTimersByTimeAsync(0);
      });
      expect(
        vi.mocked(apiModule.api.tickets.list).mock.calls.length,
      ).toBeGreaterThan(apresInit);
    } finally {
      vi.useRealTimers();
    }
  });

  it("ignores events with unknown type", async () => {
    const event = makeEvent("agent_started", { round: 1 });
    const { result, rerender } = renderHook(
      ({ events }: { events: OrchestratorEvent[] }) =>
        useTickets("proj-1", false, events),
      { initialProps: { events: [] as OrchestratorEvent[] } },
    );

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      rerender({ events: [event] });
    });

    expect(
      result.current.tickets.find((t) => t.id === "ticket-001")?.status,
    ).toBe("todo");
  });
});
