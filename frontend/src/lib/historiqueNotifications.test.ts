import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  ajouter,
  ecrireHistorique,
  historiqueVide,
  jourLocal,
  lireHistorique,
  nonLus,
  purgerSiAutreJour,
  toutMarquerLu,
} from "./historiqueNotifications";
import type { Notif } from "./notifications";

const MIDI = new Date(2026, 9, 26, 12, 0, 0);
const LENDEMAIN = new Date(2026, 9, 27, 8, 0, 0);

function notif(titre: string, type: Notif["type"] = "question"): Notif {
  return { projectId: "demineur", type, titre, corps: "corps" };
}

describe("historiqueNotifications", () => {
  beforeEach(() => window.localStorage.clear());
  afterEach(() => vi.useRealTimers());

  it("formats the local day", () => {
    expect(jourLocal(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
  });

  it("adds notifications most recent first, all unread", () => {
    const h = ajouter(historiqueVide(MIDI), [notif("a"), notif("b")], MIDI);
    const h2 = ajouter(h, [notif("c")], MIDI);
    expect(h2.items.map((e) => e.titre)).toEqual(["c", "b", "a"]);
    expect(nonLus(h2)).toBe(3);
    expect(new Set(h2.items.map((e) => e.id)).size).toBe(3);
  });

  it("counts only unread entries and marks them all read", () => {
    const h = ajouter(historiqueVide(MIDI), [notif("a"), notif("b")], MIDI);
    expect(nonLus(h)).toBe(2);
    const lu = toutMarquerLu(h);
    expect(nonLus(lu)).toBe(0);
    expect(lu.items).toHaveLength(2);
  });

  it("empties a history that belongs to a previous day", () => {
    const hier = ajouter(historiqueVide(MIDI), [notif("a")], MIDI);
    expect(purgerSiAutreJour(hier, MIDI)).toBe(hier);
    const purge = purgerSiAutreJour(hier, LENDEMAIN);
    expect(purge.items).toEqual([]);
    expect(purge.jour).toBe("2026-10-27");
  });

  it("starts a new day when a notification arrives after midnight", () => {
    const hier = ajouter(historiqueVide(MIDI), [notif("a")], MIDI);
    const h = ajouter(hier, [notif("b")], LENDEMAIN);
    expect(h.items.map((e) => e.titre)).toEqual(["b"]);
  });

  it("reads back what was written, on the same day", () => {
    const h = ajouter(historiqueVide(MIDI), [notif("a")], MIDI);
    ecrireHistorique(h);
    expect(lireHistorique(MIDI)).toEqual(h);
  });

  it("drops the stored history of a previous day when loading, with a simulated date", () => {
    ecrireHistorique(ajouter(historiqueVide(MIDI), [notif("a")], MIDI));
    vi.useFakeTimers();
    vi.setSystemTime(LENDEMAIN);
    const h = lireHistorique(new Date());
    expect(h.items).toEqual([]);
    expect(nonLus(h)).toBe(0);
  });

  it("falls back to an empty history on a stored value that makes no sense", () => {
    window.localStorage.setItem("tessera.ui.notifications.historique", JSON.stringify({ jour: 3 }));
    expect(lireHistorique(MIDI)).toEqual(historiqueVide(MIDI));
  });
});
