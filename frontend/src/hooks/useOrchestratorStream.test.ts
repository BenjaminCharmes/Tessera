import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MockWebSocket } from "../test/mockWebSocket";
import { useOrchestratorStream } from "./useOrchestratorStream";

vi.stubGlobal("WebSocket", MockWebSocket);

beforeEach(() => {
  MockWebSocket.instance = null;
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("useOrchestratorStream", () => {
  it("starts in idle state", () => {
    const { result } = renderHook(() => useOrchestratorStream("ide-core"));
    expect(result.current.status).toBe("idle");
    expect(result.current.ticketId).toBeNull();
    expect(result.current.events).toHaveLength(0);
    expect(result.current.lastResult).toBeNull();
  });

  it("transitions to connecting on connect()", () => {
    const { result } = renderHook(() => useOrchestratorStream("ide-core"));
    act(() => {
      result.current.connect("ticket-001");
    });
    expect(result.current.status).toBe("connecting");
    expect(result.current.ticketId).toBe("ticket-001");
  });

  it("transitions to running on agent_started event", () => {
    const { result } = renderHook(() => useOrchestratorStream("ide-core"));
    act(() => {
      result.current.connect("ticket-001");
    });
    act(() => {
      MockWebSocket.instance!.triggerOpen();
      MockWebSocket.instance!.triggerMessage({
        type: "agent_started",
        agent: "codeur",
        ticket_id: "ticket-001",
        data: { round: 1 },
        timestamp: "2026-06-20T00:00:00Z",
      });
    });
    expect(result.current.status).toBe("running");
    expect(result.current.currentAgent).toBe("codeur");
    expect(result.current.currentRound).toBe(1);
  });

  it("accumulates codeur tokens", () => {
    const { result } = renderHook(() => useOrchestratorStream("ide-core"));
    act(() => {
      result.current.connect("ticket-001");
      MockWebSocket.instance!.triggerOpen();
      MockWebSocket.instance!.triggerMessage({
        type: "agent_started",
        agent: "codeur",
        ticket_id: "ticket-001",
        data: { round: 1 },
        timestamp: "2026-06-20T00:00:00Z",
      });
      MockWebSocket.instance!.triggerMessage({
        type: "agent_token",
        agent: "codeur",
        ticket_id: "ticket-001",
        data: { token: "def " },
        timestamp: "2026-06-20T00:00:00Z",
      });
      MockWebSocket.instance!.triggerMessage({
        type: "agent_token",
        agent: "codeur",
        ticket_id: "ticket-001",
        data: { token: "foo():" },
        timestamp: "2026-06-20T00:00:00Z",
      });
    });
    expect(result.current.currentTokens).toBe("def foo():");
  });

  it("sets lastResult and status done on pipeline_done", () => {
    const { result } = renderHook(() => useOrchestratorStream("ide-core"));
    act(() => {
      result.current.connect("ticket-001");
      MockWebSocket.instance!.triggerOpen();
      MockWebSocket.instance!.triggerMessage({
        type: "pipeline_done",
        agent: null,
        ticket_id: "ticket-001",
        data: {
          ticket_id: "ticket-001",
          final_status: "done",
          rounds: 2,
          approved: true,
        },
        timestamp: "2026-06-20T00:00:00Z",
      });
    });
    expect(result.current.status).toBe("done");
    expect(result.current.lastResult).toMatchObject({
      ticket_id: "ticket-001",
      approved: true,
      rounds: 2,
    });
  });

  it("sets status error on error event", () => {
    const { result } = renderHook(() => useOrchestratorStream("ide-core"));
    act(() => {
      result.current.connect("ticket-001");
      MockWebSocket.instance!.triggerOpen();
      MockWebSocket.instance!.triggerMessage({
        type: "error",
        agent: null,
        ticket_id: "ticket-001",
        data: { message: "Something went wrong" },
        timestamp: "2026-06-20T00:00:00Z",
      });
    });
    expect(result.current.status).toBe("error");
    expect(result.current.errorMessage).toBe("Something went wrong");
  });

  it("clear() resets to initial state", () => {
    const { result } = renderHook(() => useOrchestratorStream("ide-core"));
    act(() => {
      result.current.connect("ticket-001");
      MockWebSocket.instance!.triggerOpen();
    });
    act(() => {
      result.current.clear();
    });
    expect(result.current.status).toBe("idle");
    expect(result.current.ticketId).toBeNull();
    expect(result.current.events).toHaveLength(0);
  });

  it("ignores null projectId on connect", () => {
    const { result } = renderHook(() => useOrchestratorStream(null));
    act(() => {
      result.current.connect("ticket-001");
    });
    // No WebSocket created when projectId is null
    expect(MockWebSocket.instance).toBeNull();
  });
});

describe("reconnexion", () => {
  it("ne relance pas le pipeline quand la connexion tombe", () => {
    // Panne vecue le 2026-09-17 : a la fermeture de la socket, le hook
    // rouvrait et renvoyait la commande de demarrage — ce qui lancait un
    // *nouveau* run. Trois runs sont partis sans que l'utilisateur ait
    // reclique, sur un ticket qui echouait vite.
    const { result } = renderHook(() => useOrchestratorStream("proj-1"));

    act(() => {
      result.current.connect("ticket-001");
    });
    const premiere = MockWebSocket.instance;

    act(() => {
      premiere?.onclose?.(new CloseEvent("close"));
      vi.advanceTimersByTime(10_000);
    });

    expect(MockWebSocket.instance).toBe(premiere);
    expect(result.current.status).toBe("error");
    expect(result.current.errorMessage).toMatch(/connexion/i);
  });
});
