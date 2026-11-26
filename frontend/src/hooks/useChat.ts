import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { createWebSocket, wsUrl, type WsMessage } from "../lib/ws";
import type { ChatMessage } from "../types/api";
import { applyFrame, nowIso, type ChatState } from "./chatFrames";

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
  sansOutils: false,
  errorMessage: null,
  lastBranch: null,
  suggestedTicketId: null,
  runningTicketId: null,
  lastRun: null,
};

const CONNECTING: ChatState = { ...INITIAL, status: "connecting" };


function messageUtilisateur(content: string): ChatMessage {
  return { role: "user", content, cost_usd: 0, ts: nowIso() };
}

/**
 * Une conversation avec l'agent du projet.
 *
 * L'historique vient du REST au montage — la conversation survit donc à un
 * rechargement — et chaque tour passe par le WebSocket, qui streame les tokens
 * et les appels d'outil au fil de leur arrivée.
 *
 * L'état est **clé** par conversation : au changement de projet, l'état
 * visible redevient « connexion » par simple comparaison de clé, sans
 * `setState` synchrone dans l'effet. Les écritures venant d'une conversation
 * qui n'est plus la courante sont ignorées.
 */
export function useChat(
  projectId: string | null,
  conversationId = "default",
): UseChatResult {
  const cle = projectId ? `${projectId}/${conversationId}` : null;
  const [memo, setMemo] = useState<{ cle: string; etat: ChatState } | null>(
    null,
  );
  const wsRef = useRef<WebSocket | null>(null);
  const cleRef = useRef<string | null>(null);
  /** Change à chaque conversation : les rappels d'une socket périmée se taisent. */
  const genRef = useRef(0);
  /** Message à faire partir dès que la socket rouverte sera prête. */
  const enAttenteRef = useRef<string | null>(null);

  const state: ChatState =
    cle === null ? INITIAL : memo && memo.cle === cle ? memo.etat : CONNECTING;

  const patch = useCallback(
    (cleCible: string, fn: (s: ChatState) => ChatState) => {
      if (cleRef.current !== cleCible) return;
      setMemo((prev) => ({
        cle: cleCible,
        etat: fn(prev && prev.cle === cleCible ? prev.etat : CONNECTING),
      }));
    },
    [],
  );

  useEffect(() => {
    cleRef.current = cle;
  }, [cle]);

  const ouvrir = useCallback(
    (gen: number): WebSocket | null => {
      if (!projectId || !cle) return null;
      const vivant = () => genRef.current === gen;
      const ws = createWebSocket(wsUrl(`/api/v1/projects/${projectId}/chat`), {
        onMessage: (data: WsMessage) => {
          if (vivant()) patch(cle, (s) => applyFrame(s, data));
        },
        onError: () => {
          if (vivant())
            patch(cle, (s) => ({
              ...s,
              status: "error",
              errorMessage: "Connexion au chat perdue.",
            }));
        },
        onClose: () => {
          if (vivant())
            patch(cle, (s) =>
              s.status === "error" ? s : { ...s, status: "disconnected" },
            );
        },
      });
      ws.onopen = () => {
        if (!vivant()) return;
        const attente = enAttenteRef.current;
        enAttenteRef.current = null;
        if (attente) {
          ws.send(attente);
          patch(cle, (s) => ({
            ...s,
            status: "thinking",
            streaming: "",
            toolUses: [],
          }));
        } else {
          patch(cle, (s) => ({ ...s, status: "ready" }));
        }
      };
      wsRef.current = ws;
      return ws;
    },
    [projectId, cle, patch],
  );

  // --- historique + socket -------------------------------------------------
  useEffect(() => {
    if (!projectId || !cle) return;
    const gen = ++genRef.current;

    api.chat
      .history(projectId, conversationId)
      .then((history) => {
        if (genRef.current !== gen) return;
        patch(cle, (s) => ({
          ...s,
          messages: history.messages,
          spentUsd: history.spent_usd,
          maxUsd: history.max_usd,
          sansOutils: history.sans_outils === true,
        }));
      })
      .catch((err: unknown) => {
        if (genRef.current !== gen) return;
        patch(cle, (s) => ({
          ...s,
          status: "error",
          errorMessage: err instanceof Error ? err.message : String(err),
        }));
      });

    ouvrir(gen);

    return () => {
      genRef.current += 1;
      enAttenteRef.current = null;
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [projectId, conversationId, cle, ouvrir, patch]);

  const send = useCallback(
    (message: string) => {
      const trimmed = message.trim();
      if (!trimmed || !cle) return;
      const payload = JSON.stringify({
        conversation_id: conversationId,
        message: trimmed,
      });
      const ws = wsRef.current;

      if (ws && ws.readyState === WebSocket.OPEN) {
        // Le message part dans le fil immédiatement : attendre l'aller-retour
        // donnerait l'impression que rien ne s'est passé.
        patch(cle, (s) => ({
          ...s,
          status: "thinking",
          streaming: "",
          toolUses: [],
          errorMessage: null,
          messages: [...s.messages, messageUtilisateur(trimmed)],
        }));
        ws.send(payload);
        return;
      }

      // Socket fermée proprement : l'envoi la rouvre, et le message part à
      // l'ouverture. Rien d'automatique avant — un serveur redémarré n'a pas
      // à recevoir une rafale de reconnexions de panneaux inactifs.
      if (state.status === "disconnected") {
        enAttenteRef.current = payload;
        patch(cle, (s) => ({
          ...s,
          status: "connecting",
          errorMessage: null,
          messages: [...s.messages, messageUtilisateur(trimmed)],
        }));
        ouvrir(genRef.current);
      }
    },
    [cle, conversationId, patch, ouvrir, state.status],
  );

  const clearError = useCallback(() => {
    if (cle) patch(cle, (s) => ({ ...s, errorMessage: null }));
  }, [cle, patch]);

  const runSuggested = useCallback(() => {
    const ticketId = state.suggestedTicketId;
    if (!projectId || !cle || !ticketId || state.runningTicketId) return;

    // La suggestion disparaît dès le clic : la laisser inviterait à relancer
    // un pipeline déjà en cours, que le backend refuserait de toute façon.
    patch(cle, (s) => ({
      ...s,
      runningTicketId: ticketId,
      suggestedTicketId: null,
      errorMessage: null,
    }));

    api.chat
      .runPipeline(projectId, conversationId, ticketId)
      .then((run) => {
        patch(cle, (s) => ({ ...s, runningTicketId: null, lastRun: run }));
      })
      .catch((err: unknown) => {
        patch(cle, (s) => ({
          ...s,
          runningTicketId: null,
          errorMessage: err instanceof Error ? err.message : String(err),
        }));
      });
  }, [
    projectId,
    cle,
    conversationId,
    patch,
    state.suggestedTicketId,
    state.runningTicketId,
  ]);

  return { ...state, send, clearError, runSuggested };
}
