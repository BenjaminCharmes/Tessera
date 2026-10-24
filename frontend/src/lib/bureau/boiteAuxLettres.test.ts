import { describe, it, expect } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { EventType, OrchestratorEvent } from "../../types/api";
import { boiteAuxLettres } from "./boiteAuxLettres";

function ev(type: EventType, data: Record<string, unknown> = {}): OrchestratorEvent {
  return { type, agent: null, ticket_id: "ticket-001", data, timestamp: "2026-01-01T00:00:00.000Z" };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const livraison = (data: Record<string, unknown>): OrchestratorEvent =>
  ev("livraison_done", { pr_number: 42, arret: null, conflits: [], merged: false, ...data });

describe("boiteAuxLettres", () => {
  it("is empty before any delivery", () => {
    expect(boiteAuxLettres(INITIAL)).toEqual({ etat: "aucune", pr: null });
  });

  it("is empty when the delivery opened no pull request", () => {
    const etat = rejouer([livraison({ pr_number: null, arret: "autonomy commit" })]);
    expect(boiteAuxLettres(etat)).toEqual({ etat: "aucune", pr: null });
  });

  it("is open when a pull request exists but the delivery stopped, as after a resolved conflict", () => {
    const etat = rejouer([livraison({ arret: "conflit résolu, PR à relire", conflits: ["a.py"] })]);
    expect(boiteAuxLettres(etat)).toEqual({ etat: "ouverte", pr: 42 });
  });

  it("waits on the CI when a pull request exists without a stop", () => {
    expect(boiteAuxLettres(rejouer([livraison({})]))).toEqual({ etat: "ci", pr: 42 });
  });

  it("waits on the CI for an orphan pull request despite its stop", () => {
    const etat = rejouer([livraison({ arret: "push failed", pr_orpheline: true })]);
    expect(boiteAuxLettres(etat)).toEqual({ etat: "ci", pr: 42 });
  });

  it("turns merged once ci_merge_done reports a merge", () => {
    const etat = rejouer([livraison({}), ev("ci_merge_done", { merged: true, arret: null })]);
    expect(boiteAuxLettres(etat)).toEqual({ etat: "mergee", pr: 42 });
  });

  it("turns refused when ci_merge_done reports no merge", () => {
    const etat = rejouer([
      livraison({}),
      ev("ci_merge_done", { merged: false, arret: "CI rouge" }),
    ]);
    expect(boiteAuxLettres(etat)).toEqual({ etat: "refusee", pr: 42 });
  });

  it("reads a ci_merge_done alone, taking the number from it", () => {
    const etat = rejouer([ev("ci_merge_done", { merged: true, pr_number: 7 })]);
    expect(boiteAuxLettres(etat)).toEqual({ etat: "mergee", pr: 7 });
  });

  it("ignores a ci_merge_done that precedes the last delivery", () => {
    const etat = rejouer([ev("ci_merge_done", { merged: true }), livraison({ pr_number: 43 })]);
    expect(boiteAuxLettres(etat)).toEqual({ etat: "ci", pr: 43 });
  });
});
