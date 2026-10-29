import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { libelleDuPoste } from "./libelleDuPoste";
import { roleDuPoste, rolesDesPostes } from "./roleDuPoste";

function ev(type: EventType, agent: AgentRole | null = null): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data: {}, timestamp: "2026-01-01T00:00:00.000Z" };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

function libelleDuCodeur(etat: StreamState): string {
  return libelleDuPoste(roleDuPoste(etat, "codeur"), "occupe", "actif");
}

describe("roleDuPoste", () => {
  it("reads the coder post as the architect after an architect start", () => {
    const etat = rejouer([ev("agent_started", "architect")]);

    expect(libelleDuCodeur(etat)).toBe("Architecte, travaille");
  });

  it("reads the coder post as the coder after a coder start", () => {
    const etat = rejouer([ev("agent_started", "codeur")]);

    expect(libelleDuCodeur(etat)).toBe("Codeur, travaille");
  });

  it("follows the last start of the post, even after the architect is done", () => {
    const architecte = rejouer([ev("agent_started", "architect"), ev("agent_done", "architect")]);
    const puisCodeur = rejouer([
      ev("agent_started", "architect"),
      ev("agent_done", "architect"),
      ev("agent_started", "codeur"),
    ]);

    expect(roleDuPoste(architecte, "codeur")).toBe("architect");
    expect(roleDuPoste(puisCodeur, "codeur")).toBe("codeur");
  });

  it("keeps the coder before any event", () => {
    expect(roleDuPoste(INITIAL, "codeur")).toBe("codeur");
  });

  it("never renames another post", () => {
    const etat = rejouer([ev("agent_started", "architect")]);

    expect(roleDuPoste(etat, "reviewer")).toBe("reviewer");
    expect(rolesDesPostes(etat)).toEqual({
      codeur: "architect",
      testeur: "testeur",
      securite: "securite",
      reviewer: "reviewer",
      validateur: "validateur",
    });
  });
});
