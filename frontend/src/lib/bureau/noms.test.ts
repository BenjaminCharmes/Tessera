import { describe, expect, it } from "vitest";
import { avecLeNom, nomDeLAgent, prenomsDeProduit } from "./noms";
import { TENUES } from "./physique";
import type { RoleAffiche } from "./postesDuRun";

const ROLES = Object.keys(TENUES) as RoleAffiche[];

describe("nomDeLAgent", () => {
  it("gives the same name to the same project and the same role", () => {
    expect(nomDeLAgent("ide-core", "codeur")).toBe(nomDeLAgent("ide-core", "codeur"));
    expect(nomDeLAgent("kadoomi", "reviewer")).toBe(nomDeLAgent("kadoomi", "reviewer"));
  });

  it("gives different names to the roles of one project", () => {
    for (const projet of ["ide-core", "kadoomi", "devinoo", "projet-0", "a", ""]) {
      const noms = ROLES.map((role) => nomDeLAgent(projet, role));
      expect(new Set(noms).size).toBe(ROLES.length);
    }
  });

  it("names every role with a non-empty first name", () => {
    for (const role of ROLES) expect(nomDeLAgent("ide-core", role).length).toBeGreaterThan(0);
  });

  it("does not depend on the roles asked before", () => {
    const seul = nomDeLAgent("ide-core", "validateur");
    ROLES.forEach((role) => nomDeLAgent("ide-core", role));
    expect(nomDeLAgent("ide-core", "validateur")).toBe(seul);
  });
});

describe("avecLeNom", () => {
  it("opens a label with the name and lowers its first letter", () => {
    const nom = nomDeLAgent("ide-core", "codeur");

    expect(avecLeNom("ide-core", "codeur", "Codeur, travaille")).toBe(`${nom}, codeur, travaille`);
  });
});

describe("prenomsDeProduit", () => {
  it("gives every product agent of a project a stable and distinct first name", () => {
    const ids = ["redacteur", "relecteur", "traducteur"];
    const premiers = prenomsDeProduit("curio", ids);
    expect(prenomsDeProduit("curio", ids)).toEqual(premiers);
    expect(new Set(premiers.values()).size).toBe(ids.length);
    expect(premiers.get("redacteur")).toMatch(/^[A-ZÉ][a-zéèëïô]+$/);
  });
});
