import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../hooks/streamState";
import type { StreamState } from "../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../types/api";
import { enEtapeSilencieuse, santeAgent } from "./santeAgent";

const DERNIER = "2026-10-26T10:00:00.000Z";
const T0 = Date.parse(DERNIER);
const MIN = 60_000;

function ev(type: EventType, agent: AgentRole | null = null): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data: {}, timestamp: DERNIER };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

function sante(etat: StreamState, silence: number) {
  return santeAgent(DERNIER, T0 + silence, etat.pendingQuestion, false, enEtapeSilencieuse(etat));
}

describe("santeAgent during a silent step (ticket-587)", () => {
  it("is waiting, never stalled, between test_started and test_result", () => {
    const etat = rejouer([ev("agent_done", "codeur"), ev("test_started")]);

    expect(sante(etat, 10 * MIN)).toBe("attente");
  });

  it("is stalled again once test_result has arrived", () => {
    const etat = rejouer([ev("test_started"), ev("test_result")]);

    expect(sante(etat, 10 * MIN)).toBe("blocage_suspecte");
  });

  it("leaves a test step without result when an agent starts again", () => {
    const etat = rejouer([ev("test_started"), ev("agent_started", "codeur")]);

    expect(enEtapeSilencieuse(etat)).toBe(false);
  });

  it.each([
    ["validation", "validation_started"],
    ["securite", "security_audit_started"],
    ["documentation", "documentation_started"],
    ["livraison", "livraison_started"],
  ] as const)("is waiting for 10 minutes during %s", (etape, evenement) => {
    const etat = rejouer([ev(evenement)]);

    expect(etat.etape).toBe(etape);
    expect(sante(etat, 10 * MIN)).toBe("attente");
  });

  it("is stalled again after the silent step is done", () => {
    const etat = rejouer([ev("validation_started"), ev("validation_done")]);

    expect(sante(etat, 10 * MIN)).toBe("blocage_suspecte");
  });

  it("still suspects a stall after 4 minutes of coder silence", () => {
    const etat = rejouer([ev("agent_started", "codeur")]);

    expect(sante(etat, 4 * MIN)).toBe("blocage_suspecte");
  });

  it("lets a pending question win over a silent step", () => {
    expect(santeAgent(DERNIER, T0 + 10 * MIN, "On casse l'API ?", false, true)).toBe("question");
  });
});
