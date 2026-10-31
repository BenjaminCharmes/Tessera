import { describe, expect, it } from "vitest";
import type { AppEnCours } from "../../types/api";
import {
  formaterMo,
  grouperParProjet,
  memoireTotale,
} from "./format";

function app(over: Partial<AppEnCours>): AppEnCours {
  return {
    project_id: "alpha",
    project_name: "Alpha",
    nom: "api",
    origine: "tessera",
    pid: 1,
    ports: [],
    demarre_a: null,
    memoire_mo: 10,
    ...over,
  };
}

describe("formaterMo", () => {
  it("shows one decimal with a French comma", () => {
    expect(formaterMo(412.5)).toBe("412,5 Mo");
    expect(formaterMo(0)).toBe("0,0 Mo");
  });
});

describe("memoireTotale", () => {
  it("sums the memory of every app", () => {
    const apps = [app({ memoire_mo: 100.5 }), app({ pid: 2, memoire_mo: 50 })];
    expect(memoireTotale(apps)).toBe(150.5);
    expect(memoireTotale([])).toBe(0);
  });
});

describe("grouperParProjet", () => {
  it("groups by project, heaviest group and heaviest app first", () => {
    const groupes = grouperParProjet([
      app({ pid: 1, nom: "petit", memoire_mo: 20 }),
      app({ pid: 2, project_id: "beta", project_name: "Beta", memoire_mo: 500 }),
      app({ pid: 3, nom: "gros", memoire_mo: 300 }),
    ]);
    expect(groupes.map((g) => g.project_id)).toEqual(["beta", "alpha"]);
    expect(groupes[1].apps.map((a) => a.nom)).toEqual(["gros", "petit"]);
    expect(groupes[1].memoire_mo).toBe(320);
  });
});
