import { describe, expect, it } from "vitest";
import {
  ajouter,
  cleArret,
  cleLancement,
  DELAI_ATTENTE_MS,
  retirer,
  trierAttentes,
} from "./enAttente";
import type { AppEnCours } from "../types/api";

const UNE: AppEnCours = {
  project_id: "alpha",
  project_name: "Alpha",
  nom: "api",
  origine: "tessera",
  pid: 7,
  ports: [],
  demarre_a: null,
  memoire_mo: 1,
};

describe("trierAttentes", () => {
  it("keeps a stop while the pid is listed", () => {
    const tri = trierAttentes({ [cleArret(7)]: 1_000 }, [UNE], 2_000);
    expect(tri.restantes).toEqual({ [cleArret(7)]: 1_000 });
    expect(tri.expirees).toEqual([]);
  });

  it("lifts a stop once the pid is gone", () => {
    expect(trierAttentes({ [cleArret(7)]: 1_000 }, [], 2_000).restantes).toEqual({});
  });

  it("lifts a launch once the project is listed, keeps it before", () => {
    const attentes = { [cleLancement("alpha")]: 1_000 };
    expect(trierAttentes(attentes, [], 2_000).restantes).toEqual(attentes);
    expect(trierAttentes(attentes, [UNE], 2_000).restantes).toEqual({});
  });

  it("expires an operation after the delay", () => {
    const tri = trierAttentes({ [cleArret(7)]: 0 }, [UNE], DELAI_ATTENTE_MS);
    expect(tri.expirees).toEqual([cleArret(7)]);
    expect(tri.restantes).toEqual({});
  });
});

describe("ajouter and retirer", () => {
  it("adds keys stamped with the time, and removes them without mutating", () => {
    const base = {};
    const avec = ajouter(base, [cleArret(1), cleArret(2)], 5);
    expect(avec).toEqual({ [cleArret(1)]: 5, [cleArret(2)]: 5 });
    expect(base).toEqual({});
    expect(retirer(avec, [cleArret(1)])).toEqual({ [cleArret(2)]: 5 });
    expect(avec[cleArret(1)]).toBe(5);
  });
});
