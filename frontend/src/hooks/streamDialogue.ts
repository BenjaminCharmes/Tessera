/**
 * Famille « dialogue et attentes » du réducteur de `streamState.ts`
 * (ticket-695) : question de l'agent et accusé de la réponse, attente
 * extérieure, conflit, repli de provider. Chaque fonction de famille rend le
 * morceau d'état à fusionner, ou null quand l'événement n'en est pas.
 */
import type { OrchestratorEvent } from "../types/api";
import { appliquerAccuse, appliquerAttente, appliquerConflit, appliquerRepli } from "./streamAttente";
import type { StreamState } from "./streamState";

function appliquerQuestion(ev: OrchestratorEvent): Partial<StreamState> {
  const question = ev.data["question"];
  const expire = ev.data["expire_a"];
  return {
    pendingQuestion: typeof question === "string" ? question : null,
    questionExpireA: typeof expire === "string" ? expire : null,
    // Une nouvelle question efface l'accusé de la réponse précédente.
    answerAck: null,
  };
}

/** Les événements de dialogue et d'attente : question, accusé, attente, conflit, repli. */
export function appliquerDialogue(
  s: StreamState,
  ev: OrchestratorEvent,
): Partial<StreamState> | null {
  switch (ev.type) {
    case "agent_question":
      return appliquerQuestion(ev);
    case "answer_ack":
      // Accusé de réception de la réponse (ticket-320, ticket-358).
      return appliquerAccuse(s, ev);
    case "external_wait":
      return appliquerAttente(ev);
    case "conflict_resolution":
      return appliquerConflit(ev);
    case "provider_fallback":
      return appliquerRepli(ev) ?? {};
    default:
      return null;
  }
}
