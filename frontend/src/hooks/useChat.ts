import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { createWebSocket, wsUrl, type WsMessage } from "../lib/ws";
import type { ChatMessage, ChatToolUse, RunFromChatResponse } from "../types/api";

type ChatStatus = "idle" | "connecting" | "ready" | "thinking" | "error";

interface ChatState {
  status: ChatStatus;
  messages: ChatMessage[];
  /** Réponse en cours de streaming, avant d'être versée dans `messages`. */
  streaming: string;
  toolUses: ChatToolUse[];
  spentUsd: number;
  maxUsd: number;
  errorMessage: string | null;
  lastBranch: string | null;
  /** Ticket que l'agent propose de lancer. L'agent suggère, l'utilisateur décide. */
  suggestedTicketId: string | null;
  /** Un pipeline lancé depuis cette conversation est en cours. */
  runningTicketId: string | null;
  lastRun: RunFromChatResponse | null;
}

export interface UseChatResult extends ChatState {
  send: (message: string) => void;
  clearError: () => void;
  /** Accepte la suggestion de l'agent et lance le pipeline. */
  runSuggested: () => void;
}

const INITIAL: ChatState = {
  status: "idle",
  messages: [],
  streaming: "",
  toolUses: [],
  spentUsd: 0,
  maxUsd: 0,
  errorMessage: null,
  lastBranch: null,
  suggestedTicketId: null,
  runningTicketId: null,
  lastRun: null,
};

function nowIso(): string {
  return new Date().toISOString();
}

/**
 * Une conversation avec l'agent du projet.
 *
 * L'historique vient du REST au montage — la conversation survit donc à un
 * rechargement — et chaque tour passe par le WebSocket, qui streame les tokens
 * et les appels d'outil au fil de leur arrivée.
 */
export function useChat(
  projectId: string | null,
  conversationId = "default",
): UseChatResult {
  const [state, setState] = useState<ChatState>(INITIAL);
  const wsRef = useRef<WebSocket | null>(null);

  // --- historique + socket -------------------------------------------------
  useEffect(() => {
    if (!projectId) {
      setState(INITIAL);
      return;
    }

    let cancelled = false;
    setState({ ...INITIAL, status: "connecting" });

    api.chat
      .history(projectId, conversationId)
      .then((history) => {
        if (cancelled) return;
        setState((s) => ({
          ...s,
          messages: history.messages,
          spentUsd: history.spent_usd,
          maxUsd: history.max_usd,
        }));
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setState((s) => ({
          ...s,
          status: "error",
          errorMessage: err instanceof Error ? err.message : String(err),
        }));
      });

    const ws = createWebSocket(wsUrl(`/api/v1/projects/${projectId}/chat`), {
      onMessage: (data: WsMessage) => {
        if (cancelled) return;
        setState((s) => applyFrame(s, data));
      },
      onError: () => {
        if (cancelled) return;
        setState((s) => ({
          ...s,
          status: "error",
          errorMessage: "Connexion au chat perdue.",
        }));
      },
      onClose: () => {
        if (cancelled) return;
        setState((s) => (s.status === "error" ? s : { ...s, status: "idle" }));
      },
    });
    ws.onopen = () => {
      if (cancelled) return;
      setState((s) => ({ ...s, status: "ready" }));
    };
    wsRef.current = ws;

    return () => {
      cancelled = true;
      wsRef.current = null;
      ws.close();
    };
  }, [projectId, conversationId]);

  const send = useCallback(
    (message: string) => {
      const trimmed = message.trim();
      const ws = wsRef.current;
      if (!trimmed || !ws || ws.readyState !== WebSocket.OPEN) return;

      // Le message part dans le fil immédiatement : attendre l'aller-retour
      // donnerait l'impression que rien ne s'est passé.
      setState((s) => ({
        ...s,
        status: "thinking",
        streaming: "",
        toolUses: [],
        errorMessage: null,
        messages: [
          ...s.messages,
          { role: "user", content: trimmed, cost_usd: 0, ts: nowIso() },
        ],
      }));
      ws.send(
        JSON.stringify({ conversation_id: conversationId, message: trimmed }),
      );
    },
    [conversationId],
  );

  const clearError = useCallback(() => {
    setState((s) => ({ ...s, errorMessage: null }));
  }, []);

  const runSuggested = useCallback(() => {
    const ticketId = state.suggestedTicketId;
    if (!projectId || !ticketId || state.runningTicketId) return;

    // La suggestion disparaît dès le clic : la laisser inviterait à relancer
    // un pipeline déjà en cours, que le backend refuserait de toute façon.
    setState((s) => ({
      ...s,
      runningTicketId: ticketId,
      suggestedTicketId: null,
      errorMessage: null,
    }));

    api.chat
      .runPipeline(projectId, conversationId, ticketId)
      .then((run) => {
        setState((s) => ({ ...s, runningTicketId: null, lastRun: run }));
      })
      .catch((err: unknown) => {
        setState((s) => ({
          ...s,
          runningTicketId: null,
          errorMessage: err instanceof Error ? err.message : String(err),
        }));
      });
  }, [projectId, conversationId, state.suggestedTicketId, state.runningTicketId]);

  return { ...state, send, clearError, runSuggested };
}

function applyFrame(s: ChatState, frame: WsMessage): ChatState {
  switch (frame["type"]) {
    case "start":
      return { ...s, status: "thinking", streaming: "", toolUses: [] };

    case "token":
      return { ...s, streaming: s.streaming + String(frame["token"] ?? "") };

    case "tool_use":
      return {
        ...s,
        toolUses: [
          ...s.toolUses,
          {
            tool: String(frame["tool"] ?? "?"),
            input: (frame["input"] as Record<string, unknown>) ?? {},
          },
        ],
      };

    case "done":
      return {
        ...s,
        status: "ready",
        streaming: "",
        messages: [
          ...s.messages,
          {
            role: "assistant",
            content: String(frame["content"] ?? ""),
            cost_usd: Number(frame["cost_usd"] ?? 0),
            ts: nowIso(),
          },
        ],
        spentUsd: Number(frame["spent_usd"] ?? s.spentUsd),
        maxUsd: Number(frame["max_usd"] ?? s.maxUsd),
        lastBranch: (frame["branch"] as string | null) ?? null,
        suggestedTicketId:
          (frame["suggested_ticket_id"] as string | null) ?? null,
      };

    case "budget_exceeded":
      return {
        ...s,
        status: "ready",
        streaming: "",
        errorMessage: String(frame["detail"] ?? "Plafond de conversation atteint."),
      };

    case "error":
      return {
        ...s,
        status: "ready",
        streaming: "",
        errorMessage: String(frame["detail"] ?? "Erreur inconnue."),
      };

    default:
      return s;
  }
}
