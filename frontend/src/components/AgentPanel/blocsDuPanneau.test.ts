import { describe, it, expect } from "vitest";
import { blocsDuPanneau } from "./blocsDuPanneau";
import type { OrchestratorEvent } from "../../types/api";

function ev(agent: string, type: string): OrchestratorEvent {
  return {
    type,
    agent,
    ticket_id: "ticket-018",
    data: {},
    timestamp: new Date().toISOString(),
    run_id: "r1",
    project_id: "demineur",
  } as OrchestratorEvent;
}

describe("blocsDuPanneau (ticket-182)", () => {
  it("montre le codeur quand l'état dit qu'il parle, sans aucun événement", () => {
    // Le cas du rechargement : les événements sont passés avant l'observateur.
    const b = blocsDuPanneau([], "codeur");

    expect(b.coderStarted).toBe(true);
    expect(b.coderDone).toBe(false);
    expect(b.reviewerStarted).toBe(false);
  });

  it("déduit que le codeur a fini quand un agent postérieur parle", () => {
    const b = blocsDuPanneau([], "reviewer");

    expect(b.coderStarted).toBe(true);
    expect(b.coderDone).toBe(true);
    expect(b.reviewerStarted).toBe(true);
  });

  it("le codeur qui parle ne fait pas croire que le reviewer a parlé", () => {
    const b = blocsDuPanneau([], "codeur");

    expect(b.coderDone).toBe(false);
    expect(b.reviewerStarted).toBe(false);
  });

  it("garde l'effet des événements quand ils sont là", () => {
    const b = blocsDuPanneau(
      [ev("codeur", "agent_started"), ev("codeur", "agent_done")],
      null,
    );

    expect(b.coderStarted).toBe(true);
    expect(b.coderDone).toBe(true);
  });

  it("un état au repos ne montre aucun bloc", () => {
    const b = blocsDuPanneau([], null);

    expect(b).toEqual({
      coderStarted: false,
      coderDone: false,
      reviewerStarted: false,
    });
  });

  it("un agent hors du pipeline ne fait rien déduire", () => {
    // Un agent que l'utilisateur vient de créer n'est nommé nulle part
    // (ADR-032). Il ne doit ni ouvrir ni fermer un bloc.
    const b = blocsDuPanneau([], "architect");

    expect(b.coderStarted).toBe(false);
    expect(b.coderDone).toBe(false);
    expect(b.reviewerStarted).toBe(false);
  });
});
