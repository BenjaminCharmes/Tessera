import { describe, it, expect } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { postesDuRun } from "./postesDuRun";
import type { EtatPoste, PosteId } from "./postesDuRun";

function ev(
  type: EventType,
  agent: AgentRole | null = null,
  data: Record<string, unknown> = {},
): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: "2026-01-01T00:00:00.000Z" };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

function etats(etat: StreamState): Record<PosteId, EtatPoste> {
  return Object.fromEntries(postesDuRun(etat).map((p) => [p.poste, p.etat])) as Record<
    PosteId,
    EtatPoste
  >;
}

const RUN_COMPLET: OrchestratorEvent[] = [
  ev("agent_started", "codeur", { round: 1 }),
  ev("agent_done", "codeur"),
  ev("test_result", null, { passed: true }),
  ev("security_audit_started"),
  ev("security_audit_done", null, { verdict: "PASS" }),
  ev("agent_started", "reviewer", { round: 1 }),
  ev("agent_done", "reviewer"),
  ev("validation_started"),
  ev("validation_done", null, { verdict: "APPROVED" }),
  ev("pipeline_done", null, { final_status: "done" }),
];

describe("postesDuRun", () => {
  it("returns the five posts in pipeline order, all free for an empty store", () => {
    expect(postesDuRun(INITIAL)).toEqual([
      { poste: "codeur", etat: "libre" },
      { poste: "testeur", etat: "libre" },
      { poste: "securite", etat: "libre" },
      { poste: "reviewer", etat: "libre" },
      { poste: "validateur", etat: "libre" },
    ]);
  });

  it("marks every finished agent as done for a closed run", () => {
    const clos = rejouer([...RUN_COMPLET, ev("run_closed")]);
    // Le piège : run_closed vide etape et etapesEnCours.
    expect(clos.etapesEnCours).toEqual([]);
    expect(clos.etape).toBeNull();
    expect(etats(clos)).toEqual({
      codeur: "fait",
      testeur: "fait",
      securite: "fait",
      reviewer: "fait",
      validateur: "fait",
    });
  });

  it("marks the reviewer busy and the coder and tester done for a run at review", () => {
    const enRevue = rejouer([
      ev("agent_started", "codeur", { round: 1 }),
      ev("agent_done", "codeur"),
      ev("test_result", null, { passed: true }),
      ev("agent_started", "reviewer", { round: 1 }),
    ]);
    expect(etats(enRevue)).toMatchObject({
      codeur: "fait",
      testeur: "fait",
      reviewer: "occupe",
      securite: "libre",
      validateur: "libre",
    });
  });

  it("marks the security and validator posts busy between their start and done events", () => {
    expect(etats(rejouer([ev("security_audit_started")])).securite).toBe("occupe");
    expect(etats(rejouer([ev("validation_started")])).validateur).toBe("occupe");
  });

  it("reads the architect as the coder post on a design ticket", () => {
    expect(etats(rejouer([ev("agent_started", "architect")])).codeur).toBe("occupe");
  });

  it("reads the plan round, announced under the coder, as the coder post", () => {
    const plan = rejouer([ev("agent_started", "codeur", { round: 0, phase: "plan" })]);
    expect(etats(plan).codeur).toBe("occupe");
  });

  it("keeps the coder busy on a second round while its first pass stays recorded", () => {
    const tour2 = rejouer([
      ev("agent_started", "codeur"),
      ev("agent_done", "codeur"),
      ev("agent_started", "codeur"),
    ]);
    expect(etats(tour2).codeur).toBe("occupe");
  });

  it("never marks the tester busy, since no event announces its start", () => {
    const apresCodeur = rejouer([ev("agent_started", "codeur"), ev("agent_done", "codeur")]);
    expect(etats(apresCodeur).testeur).toBe("libre");
  });

  it("does not keep a started but unfinished agent busy once the run is closed", () => {
    const arrete = rejouer([ev("agent_started", "codeur"), ev("run_closed")]);
    expect(etats(arrete).codeur).toBe("libre");
  });

  it("frees every post once the verdict is given, before the run closes", () => {
    const verdict = rejouer([ev("agent_started", "reviewer"), ev("pipeline_done")]);
    expect(etats(verdict).reviewer).toBe("libre");
  });

  it("only reads the events of the current ticket in a queue", () => {
    const file = rejouer([
      ...RUN_COMPLET,
      ev("queue_progress", null, { index: 1, total: 2 }),
      ev("agent_started", "codeur"),
    ]);
    expect(etats(file)).toMatchObject({ codeur: "occupe", reviewer: "libre", validateur: "libre" });
  });
});
