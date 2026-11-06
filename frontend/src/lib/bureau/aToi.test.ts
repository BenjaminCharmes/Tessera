import { describe, expect, it } from "vitest";
import { contenuAToi, prARelire } from "./aToi";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { EventType } from "../../types/api";

const T0 = Date.parse("2026-10-23T10:00:00.000Z");

function ev(type: EventType, data: Record<string, unknown> = {}) {
  return { type, agent: null, ticket_id: "ticket-001", data, timestamp: "2026-10-23T10:00:00.000Z" };
}

function rejouer(...evenements: ReturnType<typeof ev>[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

describe("prARelire", () => {
  it("returns the PR number of a resolved conflict", () => {
    const etat = rejouer(ev("livraison_done", { pr_number: 9, conflits: ["x"], arret: "conflit résolu" }));
    expect(prARelire(etat)).toBe(9);
  });

  it("returns null without conflicts, without a stop, or without a PR", () => {
    expect(prARelire(rejouer(ev("livraison_done", { pr_number: 9, conflits: [], arret: "x" })))).toBeNull();
    expect(prARelire(rejouer(ev("livraison_done", { pr_number: 9, conflits: ["x"], arret: null })))).toBeNull();
    expect(prARelire(rejouer(ev("livraison_done", { pr_number: null, conflits: ["x"], arret: "x" })))).toBeNull();
    expect(prARelire(INITIAL)).toBeNull();
  });

  it("reads only the last delivery", () => {
    const etat = rejouer(
      ev("livraison_done", { pr_number: 9, conflits: ["x"], arret: "conflit résolu" }),
      ev("livraison_done", { pr_number: 10, conflits: [], arret: null }),
    );
    expect(prARelire(etat)).toBeNull();
  });
});

describe("contenuAToi", () => {
  it("gathers questions, frozen runs and PRs to read", () => {
    const question = rejouer(ev("agent_question", { question: "Q ?", expire_a: "2026-10-23T10:08:00.000Z" }));
    const fige = rejouer(ev("agent_started"));
    const pr = rejouer(
      ev("livraison_done", { pr_number: 5, conflits: ["x"], arret: "conflit résolu" }),
      ev("run_closed"),
    );

    const contenu = contenuAToi(
      [
        { nom: "a", etat: question, runId: "r1" },
        { nom: "b", etat: fige },
        { nom: "c", etat: pr },
      ],
      T0 + 200_000,
    );

    expect(contenu.questions).toEqual([
      { projet: "a", runId: "r1", question: "Q ?", expireA: "2026-10-23T10:08:00.000Z" },
    ]);
    expect(contenu.figes).toEqual(["b"]);
    expect(contenu.prs).toEqual([{ projet: "c", pr: 5 }]);
  });

  it("lists the pending lessons of a project, and nothing at zero", () => {
    const contenu = contenuAToi(
      [{ nom: "a", etat: INITIAL }],
      T0,
      { a: 2, b: 1, c: 0 },
    );

    expect(contenu.lecons).toEqual([
      { projet: "a", nombre: 2 },
      { projet: "b", nombre: 1 },
    ]);
    expect(contenuAToi([{ nom: "a", etat: INITIAL }], T0).lecons).toEqual([]);
  });

  it("writes a supervisor line for a project with open cases, none at zero", () => {
    const contenu = contenuAToi([{ nom: "a", etat: INITIAL }], T0, {}, { a: 2, b: 0, c: 1 });

    expect(contenu.superviseur).toEqual([
      { projet: "a", nombre: 2, ligne: "2 cas du superviseur à relire" },
      { projet: "c", nombre: 1, ligne: "1 cas du superviseur à relire" },
    ]);
    expect(contenuAToi([{ nom: "a", etat: INITIAL }], T0).superviseur).toEqual([]);
  });

  it("never lists a closed run as frozen", () => {
    const clos = rejouer(ev("agent_started"), ev("run_closed"));
    expect(contenuAToi([{ nom: "a", etat: clos }], T0 + 900_000).figes).toEqual([]);
  });

  it("does not call a run frozen while it waits for an answer", () => {
    const question = rejouer(ev("agent_question", { question: "Q ?" }));
    expect(contenuAToi([{ nom: "a", etat: question }], T0 + 900_000).figes).toEqual([]);
  });
});
