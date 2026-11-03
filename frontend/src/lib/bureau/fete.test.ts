import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { EventType, OrchestratorEvent } from "../../types/api";
import { DUREE_DE_LA_FETE_MS, contourEnCelebration, enFete, gyrophareAllume } from "./fete";

const DEPART = "2026-10-27T09:00:00.000Z";
const T0 = Date.parse(DEPART);

function ev(type: EventType, data: Record<string, unknown> = {}, timestamp = DEPART): OrchestratorEvent {
  return { type, agent: null, ticket_id: "ticket-001", data, timestamp };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const livraison = ev("livraison_done", { pr_number: 7, arret: null });

describe("enFete", () => {
  it("is false before any merge", () => {
    expect(enFete(INITIAL, T0)).toBe(false);
    expect(enFete(rejouer([livraison]), T0)).toBe(false);
  });

  it("is true for 10 s after a merged ci_merge_done", () => {
    const etat = rejouer([livraison, ev("ci_merge_done", { merged: true })]);

    expect(enFete(etat, T0)).toBe(true);
    expect(enFete(etat, T0 + DUREE_DE_LA_FETE_MS - 1)).toBe(true);
    expect(enFete(etat, T0 + DUREE_DE_LA_FETE_MS)).toBe(false);
  });

  it("is false for a refused merge", () => {
    const etat = rejouer([livraison, ev("ci_merge_done", { merged: false })]);

    expect(enFete(etat, T0)).toBe(false);
  });

  it("is false when the clock reads before the event or the timestamp is unreadable", () => {
    const merge = ev("ci_merge_done", { merged: true });

    expect(enFete(rejouer([livraison, merge]), T0 - 1)).toBe(false);
    expect(enFete(rejouer([livraison, { ...merge, timestamp: "pas une date" }]), T0)).toBe(false);
  });
});

describe("gyrophareAllume", () => {
  const refus = ev("ci_merge_done", { merged: false });

  it("is on after a refused merge", () => {
    expect(gyrophareAllume(rejouer([livraison, refus]))).toBe(true);
  });

  it("is off after a merge, before any outcome, and without a run", () => {
    expect(gyrophareAllume(rejouer([livraison, ev("ci_merge_done", { merged: true })]))).toBe(false);
    expect(gyrophareAllume(rejouer([livraison]))).toBe(false);
    expect(gyrophareAllume(INITIAL)).toBe(false);
  });

  it("goes off at the next livraison_started, and on again if that delivery is refused too", () => {
    const relance = rejouer([livraison, refus, ev("livraison_started")]);
    expect(gyrophareAllume(relance)).toBe(false);

    const refusAgain = rejouer([livraison, refus, ev("livraison_started"), livraison, refus]);
    expect(gyrophareAllume(refusAgain)).toBe(true);
  });
});

describe("contourEnCelebration", () => {
  it("keeps the outline when nothing is celebrated", () => {
    expect(contourEnCelebration("amber", false, false)).toBe("amber");
  });

  it("turns green for the party and red for the beacon, the beacon first", () => {
    expect(contourEnCelebration("neutre", true, false)).toBe("vert");
    expect(contourEnCelebration("vert", false, true)).toBe("rouge");
    expect(contourEnCelebration("vert", true, true)).toBe("rouge");
  });
});
