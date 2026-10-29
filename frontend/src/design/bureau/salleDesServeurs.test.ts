import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Tests de source de la salle des serveurs — ticket-672, ADR-058.
 *
 * Le mobilier se lit dans la source : un jeton absent d'`index.css` ou une
 * teinte d'état dans un meuble ne casse aucun test de rendu.
 */
const CSS = readFileSync(join(__dirname, "..", "..", "index.css"), "utf-8");
const MOBILIER = ["Climatiseur", "CheminDeCables", "Extincteur", "PorteCoupeFeu", "DallePerforee"];

function source(nom: string): string {
  return readFileSync(join(__dirname, `${nom}.tsx`), "utf-8");
}

describe("server room furniture", () => {
  it("draws each piece from --sprite-* tokens defined in index.css, still and without a status hue", () => {
    for (const nom of MOBILIER) {
      const contenu = source(nom);
      expect(contenu, nom).toContain("--sprite-");
      expect(contenu, nom).not.toMatch(/anim-|animation|transition|data-voyant/);
      expect(contenu, nom).not.toMatch(/\b(?:fill|stroke|bg|text)-(?:zinc|red|amber|green|blue|violet)-\d/);
      for (const m of contenu.matchAll(/--sprite-([a-z0-9-]+)/g)) {
        expect(CSS, `${nom}: --sprite-${m[1]}`).toMatch(new RegExp(`--sprite-${m[1]}:`));
      }
    }
  });

  it("gives only the rack a status lamp, from the shared service tones", () => {
    const baie = source("BaieHaute");

    expect(baie).toContain("TON_VOYANT");
    expect(baie).toContain("data-voyant");
    expect(baie).not.toMatch(/anim-|animation|transition/);
  });

  it("declares the raised floor in index.css from sprite tokens", () => {
    expect(CSS).toMatch(/[.]sol-dalles\s*[{][^}]*--sprite-dalle\b/);
  });
});
