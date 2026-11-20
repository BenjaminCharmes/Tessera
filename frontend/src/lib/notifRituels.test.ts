import { beforeEach, describe, expect, it } from "vitest";
import { notificationsRituels } from "./notifRituels";
import type { Rituel } from "./apiRituels";

function rituel(surcharge: Partial<Rituel> = {}): Rituel {
  return {
    id: "r1",
    titre: "Point revenus",
    rythme: { type: "hebdo", jour: "lundi", heure: "18:30:00" },
    duree_min: 30,
    phrase: "point revenus",
    detail: "",
    projets: [],
    statut: "en_retard",
    derniere: "2026-11-09T18:30:00",
    prochaine: null,
    depasse: false,
    fait_le: null,
    reporte_jusqua: null,
    ...surcharge,
  };
}

describe("notificationsRituels", () => {
  beforeEach(() => window.localStorage.clear());

  it("notifies a new late ritual, then nothing for the same id and derniere", () => {
    const [n] = notificationsRituels([], [rituel()]);
    expect(n.type).toBe("rituel");
    expect(n.titre).toBe("Point revenus");
    expect(n.corps).toBe("En retard depuis 18:30. Dire à Claude : « point revenus ».");
    expect(notificationsRituels([], [rituel()])).toEqual([]);
  });

  it("notifies again when the same id has a new derniere", () => {
    notificationsRituels([], [rituel()]);
    const suite = notificationsRituels([rituel()], [rituel({ derniere: "2026-11-16T18:30:00" })]);
    expect(suite).toHaveLength(1);
  });

  it("ignores rituals that are not late", () => {
    expect(notificationsRituels([], [rituel({ statut: "a_venir" })])).toEqual([]);
  });
});
