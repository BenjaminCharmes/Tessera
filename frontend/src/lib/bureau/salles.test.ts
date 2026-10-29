import { describe, expect, it } from "vitest";
import { laPause, laReunion, occupantsDeLaPause, occupantsDeLaReunion } from "./salles";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { EventType } from "../../types/api";

function ev(type: EventType, data: Record<string, unknown> = {}) {
  return { type, agent: null, ticket_id: "ticket-001", data, timestamp: "2026-10-23T10:00:00.000Z" };
}

function rejouer(...evenements: ReturnType<typeof ev>[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const CONFLIT = { phase: "started", files: ["a.py", "b.py"], outcome: null };
const LIVRAISON_RESOLUE = { pr_number: 9, conflits: ["a.py"], arret: "conflit résolu" };

describe("laPause", () => {
  it("shows a run closed on an exhausted quota with its resume label", () => {
    const etat = rejouer(ev("error", { reason: "quota_exhausted", resume: "14:30 UTC" }));

    expect(laPause(etat)).toEqual({ motif: "quota", libelle: "Quota épuisé, reprise 14:30 UTC" });
  });

  it("keeps the quota pause of a queue, whose stop resets the ticket events", () => {
    const etat = rejouer(
      ev("queue_progress", { index: 2, total: 3 }),
      ev("error", { reason: "quota_exhausted", resume: "14:30 UTC" }),
      ev("pipeline_done", { approved: false }),
      ev("queue_progress", { raison: "quota_exhausted", index: 2, total: 3 }),
      ev("run_closed"),
    );

    expect(etat.runClosed).toBe(true);
    expect(etat.ticketEvents.map((e) => e.type)).toEqual(["queue_progress", "run_closed"]);
    expect(laPause(etat)).toEqual({ motif: "quota", libelle: "Quota épuisé, reprise 14:30 UTC" });
  });

  it("does not pause a queue that stopped on a budget, nor an old quota error", () => {
    const apresBudget = rejouer(
      ev("error", { reason: "quota_exhausted", resume: "14:30 UTC" }),
      ev("queue_progress", { raison: "budget", index: 2, total: 3 }),
    );
    const ticketSuivant = rejouer(
      ev("error", { reason: "quota_exhausted", resume: "14:30 UTC" }),
      ev("queue_progress", { index: 3, total: 3 }),
    );

    expect(laPause(apresBudget)).toBeNull();
    expect(laPause(ticketSuivant)).toBeNull();
  });

  it("ignores an error that is not a quota exhaustion", () => {
    expect(laPause(rejouer(ev("error", { message: "boom" })))).toBeNull();
  });

  it("shows a queue waiting on a dependency, and releases it", () => {
    const attente = { reason: "dependency", ticket: "ticket-001", pr_number: 12 };
    const enAttente = rejouer(ev("external_wait", { ...attente, waiting: true }));

    expect(laPause(enAttente)).toEqual({ motif: "dependance", libelle: "Attend le merge de la PR #12" });
    expect(laPause(applyEvent(enAttente, ev("external_wait", { ...attente, waiting: false })))).toBeNull();
  });

  it("shows the CI of phase 2 from the mailbox", () => {
    const etat = rejouer(ev("livraison_done", { pr_number: 4, arret: null }));

    expect(laPause(etat)).toEqual({ motif: "ci", libelle: "CI en cours de la PR #4" });
  });

  it("keeps a pull request in the break room once the queue moved to the next ticket", () => {
    const etat = rejouer(
      ev("livraison_done", { pr_number: 7, arret: null }),
      ev("queue_progress", { index: 2, total: 3 }),
    );

    expect(etat.ticketEvents.map((e) => e.type)).toEqual(["queue_progress"]);
    expect(laPause(etat)).toEqual({ motif: "ci", libelle: "CI en cours de la PR #7" });
  });

  it("releases the pull request once its ci_merge_done arrives", () => {
    const etat = rejouer(
      ev("livraison_done", { pr_number: 7, arret: null }),
      ev("queue_progress", { index: 2, total: 3 }),
      ev("ci_merge_done", { pr_number: 7, merged: true }),
    );

    expect(laPause(etat)).toBeNull();
  });

  it("keeps waiting for another pull request when only one of them is merged", () => {
    const etat = rejouer(
      ev("livraison_done", { pr_number: 7, arret: null }),
      ev("queue_progress", { index: 2, total: 3 }),
      ev("livraison_done", { pr_number: 8, arret: null }),
      ev("queue_progress", { index: 3, total: 3 }),
      ev("ci_merge_done", { pr_number: 8, merged: true }),
    );

    expect(laPause(etat)).toEqual({ motif: "ci", libelle: "CI en cours de la PR #7" });
  });

  it("does not pause for a delivery that stopped without an orphan pull request", () => {
    const etat = rejouer(
      ev("livraison_done", { pr_number: 7, arret: "conflit résolu" }),
      ev("queue_progress", { index: 2, total: 3 }),
    );

    expect(laPause(etat)).toBeNull();
  });

  it("pauses for an orphan pull request despite its stop", () => {
    const etat = rejouer(
      ev("livraison_done", { pr_number: 7, arret: "push refusé", pr_orpheline: true }),
      ev("queue_progress", { index: 2, total: 3 }),
    );

    expect(laPause(etat)).toEqual({ motif: "ci", libelle: "CI en cours de la PR #7" });
  });

  it("shows nothing for a run at work", () => {
    expect(laPause(INITIAL)).toBeNull();
  });
});

describe("laReunion", () => {
  it("lists the files while the resolver works", () => {
    expect(laReunion(rejouer(ev("conflict_resolution", CONFLIT)))).toEqual({
      temps: "conflit",
      fichiers: ["a.py", "b.py"],
    });
  });

  it("shows the PR to read once the conflict is resolved", () => {
    const etat = rejouer(
      ev("conflict_resolution", CONFLIT),
      ev("conflict_resolution", { phase: "ended", files: ["a.py"], outcome: "resolved" }),
      ev("livraison_done", LIVRAISON_RESOLUE),
    );

    expect(laReunion(etat)).toEqual({ temps: "relecture", pr: 9 });
  });

  it("shows nothing after a cancelled resolution", () => {
    const etat = rejouer(
      ev("conflict_resolution", CONFLIT),
      ev("conflict_resolution", { phase: "ended", files: [], outcome: "cancelled" }),
    );

    expect(laReunion(etat)).toBeNull();
  });

  it("shows nothing for an ordinary delivery", () => {
    expect(laReunion(rejouer(ev("livraison_done", { pr_number: 4, conflits: [], arret: null })))).toBeNull();
  });
});

describe("occupants", () => {
  it("keeps only the projects that are in the room", () => {
    const projets = [
      { nom: "alpha", etat: rejouer(ev("error", { reason: "quota_exhausted", resume: "14:30 UTC" })) },
      { nom: "beta", etat: INITIAL },
      { nom: "gamma", etat: rejouer(ev("conflict_resolution", CONFLIT)) },
    ];

    expect(occupantsDeLaPause(projets).map((o) => o.projet)).toEqual(["alpha"]);
    expect(occupantsDeLaReunion(projets).map((o) => o.projet)).toEqual(["gamma"]);
  });
});
