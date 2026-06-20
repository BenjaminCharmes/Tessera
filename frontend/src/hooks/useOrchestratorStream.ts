import { useRef, useState } from "react";
import { wsUrl } from "../lib/ws";
import type {
  AgentRole,
  OrchestratorEvent,
  PipelineResult,
  TicketStatus,
} from "../types/api";

type StreamStatus = "idle" | "connecting" | "running" | "done" | "error";

interface StreamState {
  status: StreamStatus;
  ticketId: string | null;
  events: OrchestratorEvent[];
  currentAgent: AgentRole | null;
  currentRound: number;
  currentTokens: string;
  lastResult: PipelineResult | null;
  errorMessage: string | null;
}

export interface UseOrchestratorStreamResult extends StreamState {
  connect: (ticketId: string) => void;
  disconnect: () => void;
  clear: () => void;
}

const INITIAL: StreamState = {
  status: "idle",
  ticketId: null,
  events: [],
  currentAgent: null,
  currentRound: 0,
  currentTokens: "",
  lastResult: null,
  errorMessage: null,
};

function applyEvent(s: StreamState, ev: OrchestratorEvent): StreamState {
  const events = [...s.events, ev];
  switch (ev.type) {
    case "agent_started":
      return {
        ...s,
        events,
        status: "running",
        currentAgent: ev.agent,
        currentRound:
          typeof ev.data["round"] === "number"
            ? ev.data["round"]
            : s.currentRound,
        currentTokens: "",
      };
    case "agent_token":
      return {
        ...s,
        events,
        currentTokens:
          ev.agent === "codeur"
            ? s.currentTokens +
              (typeof ev.data["token"] === "string" ? ev.data["token"] : "")
            : s.currentTokens,
      };
    case "pipeline_done": {
      const result: PipelineResult = {
        ticket_id:
          typeof ev.data["ticket_id"] === "string"
            ? ev.data["ticket_id"]
            : (s.ticketId ?? ""),
        final_status: (ev.data["final_status"] as TicketStatus) ?? "done",
        rounds: typeof ev.data["rounds"] === "number" ? ev.data["rounds"] : 0,
        approved: ev.data["approved"] === true,
      };
      return { ...s, events, status: "done", lastResult: result };
    }
    case "error":
      return {
        ...s,
        events,
        status: "error",
        errorMessage:
          typeof ev.data["message"] === "string"
            ? ev.data["message"]
            : "Pipeline error",
      };
    default:
      return { ...s, events };
  }
}

export function useOrchestratorStream(
  projectId: string | null,
): UseOrchestratorStreamResult {
  const [state, setState] = useState<StreamState>(INITIAL);
  const wsRef = useRef<WebSocket | null>(null);
  const retryCountRef = useRef(0);
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const ticketIdRef = useRef<string | null>(null);
  const isDoneRef = useRef(false);

  function clearTimers() {
    if (retryTimerRef.current) {
      clearTimeout(retryTimerRef.current);
      retryTimerRef.current = null;
    }
  }

  function closeWs() {
    if (wsRef.current) {
      wsRef.current.onopen = null;
      wsRef.current.onmessage = null;
      wsRef.current.onclose = null;
      wsRef.current.onerror = null;
      wsRef.current.close();
      wsRef.current = null;
    }
  }

  function openSocket(ticketId: string) {
    if (!projectId) return;
    closeWs();

    setState((s) => ({
      ...s,
      status: "connecting",
      ticketId,
      currentTokens: "",
      currentAgent: null,
      currentRound: 0,
      errorMessage: null,
    }));

    const ws = new WebSocket(wsUrl(`/api/v1/orchestrator/stream/${projectId}`));
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ ticket_id: ticketId }));
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const ev = JSON.parse(event.data as string) as OrchestratorEvent;
        if (ev.type === "pipeline_done") isDoneRef.current = true;
        setState((s) => applyEvent(s, ev));
      } catch {
        // ignore malformed frames
      }
    };

    ws.onclose = () => {
      if (isDoneRef.current) return;

      if (retryCountRef.current < 3) {
        const delay = 1000 * Math.pow(2, retryCountRef.current);
        retryCountRef.current += 1;
        retryTimerRef.current = setTimeout(() => {
          if (ticketIdRef.current) openSocket(ticketIdRef.current);
        }, delay);
      } else {
        setState((s) => ({
          ...s,
          status: "error",
          errorMessage: "Connection lost after 3 retries",
        }));
      }
    };
  }

  function connect(ticketId: string) {
    clearTimers();
    retryCountRef.current = 0;
    ticketIdRef.current = ticketId;
    isDoneRef.current = false;
    setState({ ...INITIAL, ticketId });
    openSocket(ticketId);
  }

  function disconnect() {
    clearTimers();
    retryCountRef.current = 0;
    isDoneRef.current = true;
    closeWs();
    setState((s) => ({ ...s, status: "idle" }));
  }

  function clear() {
    clearTimers();
    retryCountRef.current = 0;
    isDoneRef.current = true;
    ticketIdRef.current = null;
    closeWs();
    setState(INITIAL);
  }

  return { ...state, connect, disconnect, clear };
}
