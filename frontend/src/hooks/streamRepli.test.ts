import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "./streamState";
import { rattacherAuRun } from "./supervisionEvents";
import type { OrchestratorEvent, RunActif } from "../types/api";

const HORODATAGE = "2026-10-27T10:00:00.000Z";

function repli(over: Partial<OrchestratorEvent> = {}): OrchestratorEvent {
  return {
    type: "provider_fallback",
    agent: null,
    ticket_id: "",
    data: { role: "validateur", tente: "ollama", utilise: "anthropic", modele: "haiku", raison: "hors ligne" },
    timestamp: HORODATAGE,
    project_id: "alpha",
    ...over,
  };
}

function run(over: Partial<RunActif>): RunActif {
  return { run_id: "r1", project_id: "alpha", mode: "single", ticket_id: null, ...over } as RunActif;
}

describe("provider_fallback in the run state (ticket-597)", () => {
  it("keeps the role, both providers, the model and the instant", () => {
    const s = applyEvent(INITIAL, repli());

    expect(s.repli).toEqual({
      role: "validateur",
      tente: "ollama",
      utilise: "anthropic",
      modele: "haiku",
      a: Date.parse(HORODATAGE),
    });
  });

  it("keeps the previous fallback when the event names no role", () => {
    const s = applyEvent(applyEvent(INITIAL, repli()), repli({ data: {} }));

    expect(s.repli?.role).toBe("validateur");
  });

  it("survives the next ticket of a queue, since it belongs to the run", () => {
    const ticketSuivant: OrchestratorEvent = {
      type: "queue_progress",
      agent: null,
      ticket_id: "ticket-002",
      data: { index: 1, total: 2 },
      timestamp: HORODATAGE,
    };

    expect(applyEvent(applyEvent(INITIAL, repli()), ticketSuivant).repli?.role).toBe("validateur");
  });
});

const AUCUN_CLOS = (): boolean => false;

describe("rattacherAuRun", () => {
  it("gives a fallback without run_id the live run of its project", () => {
    const runs = [run({ run_id: "r9", project_id: "beta" }), run({})];

    expect(rattacherAuRun(repli(), runs, AUCUN_CLOS).run_id).toBe("r1");
  });

  it("skips a closed run of the project still listed before the live one", () => {
    const runs = [run({ run_id: "ancien" }), run({ run_id: "vivant" })];

    const rattache = rattacherAuRun(repli(), runs, (id) => id === "ancien");

    expect(rattache.run_id).toBe("vivant");
  });

  it("takes the most recent run when several of the project are live", () => {
    const runs = [run({ run_id: "a" }), run({ run_id: "b" })];

    expect(rattacherAuRun(repli(), runs, AUCUN_CLOS).run_id).toBe("b");
  });

  it("leaves the event alone when every run of the project is closed", () => {
    expect(rattacherAuRun(repli(), [run({})], () => true).run_id).toBeUndefined();
  });

  it("leaves the event alone when no live run belongs to the project", () => {
    const runs = [run({ project_id: "beta" })];

    expect(rattacherAuRun(repli(), runs, AUCUN_CLOS).run_id).toBeUndefined();
  });

  it("never rewrites an event that already carries its run", () => {
    expect(rattacherAuRun(repli({ run_id: "r7" }), [run({})], AUCUN_CLOS).run_id).toBe("r7");
  });

  it("leaves other event types alone", () => {
    const autre = repli({ type: "agent_done" });

    expect(rattacherAuRun(autre, [run({})], AUCUN_CLOS)).toBe(autre);
  });
});
