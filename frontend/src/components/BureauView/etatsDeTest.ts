import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";

/** Instant du dernier événement de tous les états de test. */
export const DERNIER = "2026-10-23T10:00:00.000Z";
export const T0 = Date.parse(DERNIER);

function ev(type: EventType, agent: AgentRole | null = null): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data: {}, timestamp: DERNIER };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

/** Codeur et testeur faits, sécurité occupée, reviewer et validateur libres. */
export function etatEnSecurite(): StreamState {
  return rejouer([
    ev("agent_started", "codeur"),
    ev("agent_done", "codeur"),
    ev("test_result"),
    ev("security_audit_started"),
  ]);
}

/** Codeur, testeur, sécurité et reviewer faits ; seul le validateur n'a pas commencé. */
export function etatQuatreFaits(): StreamState {
  return rejouer([
    ev("agent_started", "codeur"),
    ev("agent_done", "codeur"),
    ev("test_result"),
    ev("security_audit_started"),
    ev("security_audit_done"),
    ev("agent_started", "reviewer"),
    ev("agent_done", "reviewer"),
  ]);
}

/** Le pipeline fini, puis les événements de suite donnés (documentation, livraison, clôture). */
export function etatApresPipeline(suite: EventType[]): StreamState {
  return rejouer([
    ev("agent_started", "codeur"),
    ev("agent_done", "codeur"),
    ev("pipeline_done"),
    ...suite.map((type) => ev(type)),
  ]);
}

/** Le codeur démarre : un seul poste occupé, les autres libres. */
export function etatEnCodage(): StreamState {
  return rejouer([ev("agent_started", "codeur")]);
}
