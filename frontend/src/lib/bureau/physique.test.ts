import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { TENUES, physique } from "./physique";
import { POSTES } from "./postesDuRun";

const CSS = readFileSync(join(__dirname, "..", "..", "index.css"), "utf-8");

/** La valeur d'un jeton `--sprite-*` déclaré dans index.css. */
function jeton(nom: string): string | undefined {
  return CSS.match(new RegExp(`--sprite-${nom}:\\s*([^;]+);`))?.[1]?.trim();
}

describe("physique", () => {
  it("gives the same look twice for the same project and role", () => {
    expect(physique("ide-core", "codeur")).toEqual(physique("ide-core", "codeur"));
  });

  it("differs between two projects on at least one trait", () => {
    expect(physique("ide-core", "codeur")).not.toEqual(physique("kadoomi", "codeur"));
  });

  it("keeps every trait inside its table", () => {
    for (const projet of ["ide-core", "kadoomi", "serpent"]) {
      for (const role of POSTES) {
        const p = physique(projet, role);
        expect([1, 2, 3, 4, 5]).toContain(p.peau);
        expect([1, 2, 3, 4, 5, 6]).toContain(p.cheveux);
        expect(["court", "long", "carre", "chauve"]).toContain(p.coiffure);
        if (p.jupe) expect(["long", "carre"]).toContain(p.coiffure);
      }
    }
  });

  it("declares a token for every skin and hair index it can draw", () => {
    for (const n of [1, 2, 3, 4, 5]) expect(jeton(`peau-${n}`), `peau-${n}`).toBeDefined();
    for (const n of [1, 2, 3, 4, 5, 6]) expect(jeton(`cheveux-${n}`), `cheveux-${n}`).toBeDefined();
  });
});

describe("TENUES", () => {
  it("gives the five roles five distinct top colours", () => {
    const hauts = POSTES.map((role) => jeton(`haut-${TENUES[role].haut}`));

    expect(hauts.every((h) => h !== undefined)).toBe(true);
    expect(new Set(hauts).size).toBe(5);
  });

  it("gives each top a shade for the arms, different from the top", () => {
    for (const role of POSTES) {
      const haut = TENUES[role].haut;
      const ombre = jeton(`haut-${haut}-ombre`);
      expect(ombre, role).toBeDefined();
      expect(ombre, role).not.toBe(jeton(`haut-${haut}`));
    }
  });

  it("dresses the architect differently from the coder, with tokens for both shades", () => {
    expect(TENUES.architect).not.toEqual(TENUES.codeur);
    expect(TENUES.architect.haut).not.toBe(TENUES.codeur.haut);
    const haut = jeton(`haut-${TENUES.architect.haut}`);
    expect(haut).toBeDefined();
    expect(haut).not.toBe(jeton("haut-codeur"));
    expect(jeton(`haut-${TENUES.architect.haut}-ombre`)).toBeDefined();
  });

  it("dresses the resolver and the two writers with their own tokens, none shared with a pipeline role", () => {
    const hautsDuPipeline = POSTES.map((role) => jeton(`haut-${TENUES[role].haut}`));

    for (const role of ["resolveur", "doc-technique", "doc-fonctionnelle"] as const) {
      const haut = jeton(`haut-${TENUES[role].haut}`);
      expect(haut, role).toBeDefined();
      expect(hautsDuPipeline, role).not.toContain(haut);
      expect(jeton(`haut-${TENUES[role].haut}-ombre`), role).toBeDefined();
      expect(jeton(`haut-${TENUES[role].haut}-ombre`), role).not.toBe(haut);
    }
    const hauts = (["resolveur", "doc-technique", "doc-fonctionnelle"] as const).map((r) => TENUES[r].haut);
    expect(new Set(hauts).size).toBe(3);
  });

  it("puts the tie on the reviewer and the hood on the coder only", () => {
    expect(POSTES.filter((r) => TENUES[r].cravate)).toEqual(["reviewer"]);
    expect(POSTES.filter((r) => TENUES[r].capuche)).toEqual(["codeur"]);
  });
});
