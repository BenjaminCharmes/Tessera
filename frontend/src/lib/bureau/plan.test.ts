import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { estTourDePlan, posteEnPlan } from "./plan";
import { postesDuRun } from "./postesDuRun";

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

const PLAN = { round: 0, phase: "plan" };

describe("estTourDePlan", () => {
  it("recognises the plan start and the plan done, and nothing else", () => {
    expect(estTourDePlan(ev("agent_started", "codeur", PLAN))).toBe(true);
    expect(estTourDePlan(ev("agent_done", "codeur", PLAN))).toBe(true);
    expect(estTourDePlan(ev("agent_started", "codeur", { round: 1 }))).toBe(false);
    expect(estTourDePlan(ev("test_started", null, PLAN))).toBe(false);
  });
});

describe("posteEnPlan", () => {
  it("is the coder post between the plan start and the plan done", () => {
    expect(posteEnPlan(rejouer([ev("agent_started", "codeur", PLAN)]))).toBe("codeur");
  });

  it("goes back to nobody once the plan is done", () => {
    const etat = rejouer([ev("agent_started", "codeur", PLAN), ev("agent_done", "codeur", PLAN)]);

    expect(posteEnPlan(etat)).toBeNull();
  });

  it("is closed by the first coder round when the plan failed without a done", () => {
    const etat = rejouer([ev("agent_started", "codeur", PLAN), ev("agent_started", "codeur", { round: 1 })]);

    expect(posteEnPlan(etat)).toBeNull();
  });

  it("is nobody in a run with no plan, and in a closed run", () => {
    expect(posteEnPlan(rejouer([ev("agent_started", "codeur", { round: 1 })]))).toBeNull();
    expect(posteEnPlan(INITIAL)).toBeNull();
    const clos = rejouer([ev("agent_started", "codeur", PLAN), ev("run_closed")]);
    expect(posteEnPlan(clos)).toBeNull();
  });
});

describe("postesDuRun around a plan", () => {
  it("shows the coder post busy during the plan, then waiting rather than done", () => {
    const pendant = rejouer([ev("agent_started", "codeur", PLAN)]);
    const apres = rejouer([ev("agent_started", "codeur", PLAN), ev("agent_done", "codeur", PLAN)]);

    expect(postesDuRun(pendant)[0]?.etat).toBe("occupe");
    expect(postesDuRun(apres)[0]?.etat).toBe("libre");
  });
});
