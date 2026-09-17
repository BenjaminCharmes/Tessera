import { useRef, useState } from "react";
import { wsUrl } from "../lib/ws";
import type {
  AgentRole,
  OrchestratorEvent,
  PipelineResult,
  QuotaState,
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
  /** Dernier état connu du quota d'abonnement, ou null tant que rien n'est remonté. */
  quota: QuotaState | null;
  /** Question posée par l'agent en cours, tant qu'on n'y a pas répondu (ticket-066). */
  pendingQuestion: string | null;
}

export interface UseOrchestratorStreamResult extends StreamState {
  connect: (ticketId: string) => void;
  disconnect: () => void;
  clear: () => void;
  /** Répond à la question en cours et laisse le run reprendre. */
  answer: (text: string) => void;
  /** Dépose une consigne, lue par le prochain agent à parler. */
  interject: (text: string) => void;
  /** Demande l'arrêt du run ; il commitera ce qu'il a déjà produit. */
  stop: () => void;
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
  quota: null,
  pendingQuestion: null,
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
      return {
        ...s,
        events,
        status: "done",
        lastResult: result,
        pendingQuestion: null,
      };
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
    case "agent_question":
      return {
        ...s,
        events,
        pendingQuestion:
          typeof ev.data["question"] === "string" ? ev.data["question"] : null,
      };
    case "quota_updated":
      // Le quota d'abonnement est la ressource réellement finie : l'afficher
      // évite d'être coupé sans comprendre pourquoi (ticket-054).
      return { ...s, events, quota: ev.data as unknown as QuotaState };

    default:
      return { ...s, events };
  }
}

export function useOrchestratorStream(
  projectId: string | null,
): UseOrchestratorStreamResult {
  const [state, setState] = useState<StreamState>(INITIAL);
  const wsRef = useRef<WebSocket | null>(null);
  const ticketIdRef = useRef<string | null>(null);
  const isDoneRef = useRef(false);

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

      // On ne se reconnecte pas. Rouvrir la socket renvoyait la commande de
      // démarrage, donc lançait un **nouveau** run : le 2026-09-17, trois runs
      // sont partis sur un ticket qui échouait vite, sans que personne n'ait
      // recliqué. Tant qu'il n'existe pas de protocole pour se rattacher à un
      // run en cours, perdre l'affichage coûte moins cher que relancer le
      // travail (ticket-068).
      setState((s) => ({
        ...s,
        status: "error",
        errorMessage:
          "Connexion au pipeline perdue. Le run continue peut-être côté serveur : " +
          "vérifie l'historique avant de relancer le ticket.",
      }));
    };
  }

  function send(payload: Record<string, string>) {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }

  function answer(text: string) {
    send({ type: "answer", text });
    // La question disparaît dès l'envoi : le backend ne réémet rien, et
    // laisser le formulaire à l'écran donnerait à croire que la réponse
    // n'est pas partie.
    setState((s) => ({ ...s, pendingQuestion: null }));
  }

  function interject(text: string) {
    send({ type: "interject", text });
  }

  function stop() {
    send({ type: "stop", text: "" });
  }

  function connect(ticketId: string) {
    ticketIdRef.current = ticketId;
    isDoneRef.current = false;
    setState({ ...INITIAL, ticketId });
    openSocket(ticketId);
  }

  function disconnect() {
    isDoneRef.current = true;
    closeWs();
    setState((s) => ({ ...s, status: "idle" }));
  }

  function clear() {
    isDoneRef.current = true;
    ticketIdRef.current = null;
    closeWs();
    setState(INITIAL);
  }

  return { ...state, connect, disconnect, clear, answer, interject, stop };
}
