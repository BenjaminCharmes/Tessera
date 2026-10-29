import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { avecLeNom } from "../../lib/bureau/noms";
import type { RoleAffiche } from "../../lib/bureau/postesDuRun";

/** Le libellé d'un poste tel que la pièce le nomme : « Codeur, travaille » devient « <prénom>, codeur, travaille ». */
export function nomme(libelle: string, role: RoleAffiche, projet = "ide-core"): string {
  return avecLeNom(projet, role, libelle);
}

/** Instant du dernier événement de tous les états de test. */
export const DERNIER = "2026-10-23T10:00:00.000Z";
export const T0 = Date.parse(DERNIER);

function ev(
  type: EventType,
  agent: AgentRole | null = null,
  data: Record<string, unknown> = {},
): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: DERNIER };
}

/** Un événement de la phase 2 (livraison, issue de la CI) avec ses données, daté de `DERNIER`. */
export interface EvenementDeSuite {
  type: EventType;
  data?: Record<string, unknown>;
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

/**
 * Le tour 1 refusé par `refus`, puis le codeur qui repart au tour 2 : reviewer
 * (`CHANGES_REQUESTED`) ou validateur (`approved: false`) a renvoyé le travail.
 */
export function etatAuTourDeux(refus: "reviewer" | "validateur"): StreamState {
  const verdict = refus === "reviewer" ? "CHANGES_REQUESTED" : "APPROVED";
  const texteDuReviewer = refus === "reviewer" ? "CHANGES_REQUESTED\n- il manque un test" : "APPROVED";
  const validation =
    refus === "validateur"
      ? [
          ev("validation_started"),
          ev("validation_done", null, { verdict: "CHANGES_REQUESTED", approved: false }),
        ]
      : [];
  return rejouer([
    ev("agent_started", "codeur", { round: 1 }),
    ev("agent_done", "codeur"),
    ev("test_result"),
    ev("security_audit_started"),
    ev("security_audit_done"),
    ev("agent_started", "reviewer", { round: 1 }),
    ev("agent_done", "reviewer", { content: texteDuReviewer, verdict }),
    ...validation,
    ev("agent_started", "codeur", { round: 2 }),
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

/** Le pipeline fini, puis des événements qui portent des données : `livraison_done`, `ci_merge_done`. */
export function etatApresPhase2(suite: EvenementDeSuite[]): StreamState {
  return rejouer([
    ev("agent_started", "codeur"),
    ev("agent_done", "codeur"),
    ev("pipeline_done"),
    ...suite.map(({ type, data }) => ev(type, null, data)),
  ]);
}

/** Le codeur démarre : un seul poste occupé, les autres libres. */
export function etatEnCodage(): StreamState {
  return rejouer([ev("agent_started", "codeur")]);
}
