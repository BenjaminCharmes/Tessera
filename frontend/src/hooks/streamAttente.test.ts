import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "./streamState";
import type { EventType, OrchestratorEvent } from "../types/api";

function ev(type: EventType, data: Record<string, unknown>): OrchestratorEvent {
  return { type, agent: null, ticket_id: "ticket-001", data, timestamp: "2026-10-23T10:00:00.000Z" };
}

const ATTENTE = { reason: "dependency", ticket: "ticket-001", pr_number: 12 };

describe("external_wait and conflict_resolution in the run state (ticket-564)", () => {
  it("accepts both types in the EventType union", () => {
    const types: EventType[] = ["external_wait", "conflict_resolution"];

    expect(types.map((type) => applyEvent(INITIAL, ev(type, {})).events[0].type)).toEqual(types);
  });

  it("puts the run on hold with waiting true and releases it with waiting false", () => {
    const enAttente = applyEvent(INITIAL, ev("external_wait", { ...ATTENTE, waiting: true }));
    expect(enAttente.attenteExterieure).toEqual({ raison: "dependency", pr: 12 });

    const repris = applyEvent(enAttente, ev("external_wait", { ...ATTENTE, waiting: false }));
    expect(repris.attenteExterieure).toBeNull();
  });

  it("keeps the PR as null when the wait does not name one", () => {
    const s = applyEvent(INITIAL, ev("external_wait", { reason: "dependency", waiting: true, pr_number: null }));

    expect(s.attenteExterieure).toEqual({ raison: "dependency", pr: null });
  });

  it("sets the conflict files on started and clears them on ended", () => {
    const enCours = applyEvent(
      INITIAL,
      ev("conflict_resolution", { phase: "started", files: ["a.py", "b.py"], outcome: null }),
    );
    expect(enCours.conflitEnCours).toEqual(["a.py", "b.py"]);

    const fini = applyEvent(
      enCours,
      ev("conflict_resolution", { phase: "ended", files: ["a.py"], outcome: "resolved" }),
    );
    expect(fini.conflitEnCours).toBeNull();
  });

  it("clears the conflict on a cancelled resolution", () => {
    const enCours = applyEvent(INITIAL, ev("conflict_resolution", { phase: "started", files: ["a.py"] }));

    const annule = applyEvent(enCours, ev("conflict_resolution", { phase: "ended", files: [], outcome: "cancelled" }));

    expect(annule.conflitEnCours).toBeNull();
  });

  it("resets both fields on the next queue ticket", () => {
    const s = [
      ev("external_wait", { ...ATTENTE, waiting: true }),
      ev("conflict_resolution", { phase: "started", files: ["a.py"] }),
      ev("queue_progress", { index: 2, total: 3 }),
    ].reduce(applyEvent, INITIAL);

    expect(s.attenteExterieure).toBeNull();
    expect(s.conflitEnCours).toBeNull();
  });
});
