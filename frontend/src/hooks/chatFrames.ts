import type { WsMessage } from "../lib/ws";
import type { ChatMessage, ChatToolUse, RunFromChatResponse } from "../types/api";

/**
 * `disconnected` est distinct d'`idle` : `idle`, c'est « aucun projet » ;
 * `disconnected`, c'est une socket fermée proprement sur un projet ouvert.
 * Les confondre laissait la zone de saisie active et le bouton grisé, sans
 * message ni moyen de repartir (ticket-123).
 */
export type ChatStatus =
  | "idle"
  | "connecting"
  | "ready"
  | "thinking"
  | "disconnected"
  | "error";

export interface ChatState {
  status: ChatStatus;
  messages: ChatMessage[];
  /** Réponse en cours de streaming, avant d'être versée dans `messages`. */
  streaming: string;
  toolUses: ChatToolUse[];
  spentUsd: number;
  maxUsd: number;
  /** Le chat de ce projet n'a aucun outil (ADR-094). */
  sansOutils: boolean;
  errorMessage: string | null;
  lastBranch: string | null;
  /** Ticket que l'agent propose de lancer. L'agent suggère, l'utilisateur décide. */
  suggestedTicketId: string | null;
  /** Un pipeline lancé depuis cette conversation est en cours. */
  runningTicketId: string | null;
  lastRun: RunFromChatResponse | null;
}

export function nowIso(): string {
  return new Date().toISOString();
}

export function applyFrame(s: ChatState, frame: WsMessage): ChatState {
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
