import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";

/**
 * Tests de source de la salle des serveurs — ticket-672, ADR-058.
 *
 * Le mobilier se lit dans la source : une teinte d'état ou une animation dans un
 * meuble ne casse aucun test de rendu. Les jetons du moteur, eux, sont vérifiés
 * contre le thème par `theme.test.ts`.
 */
const CSS = readFileSync(join(__dirname, "..", "..", "index.css"), "utf-8");
const MOBILIER = ["Climatiseur", "CheminDeCables", "Extincteur", "PorteCoupeFeu"];

function source(nom: string): string {
  return readFileSync(join(__dirname, `${nom}.tsx`), "utf-8");
}

describe("server room furniture", () => {
  it("draws each piece from the sprite engine, still and without a status hue", () => {
    for (const nom of MOBILIER) {
      const contenu = source(nom);
      // Le dessin vient du moteur (ticket-727) : ses couleurs sont des jetons --sprite-* du thème.
      expect(contenu, nom).toMatch(/lib\/bureau\/sprites\/|from "\.\/Tuile"/);
      expect(contenu, nom).not.toMatch(/anim-|animation|transition|data-voyant/);
      expect(contenu, nom).not.toMatch(/\b(?:fill|stroke|bg|text)-(?:zinc|red|amber|green|blue|violet)-\d/);
    }
  });

  it("gives only the rack a status lamp, and says which", () => {
    const baie = source("BaieHaute");

    expect(baie).toContain("data-voyant");
    expect(baie).not.toMatch(/anim-|animation|transition/);
  });

  it("lays the raised floor as a tile of plain and perforated slabs", () => {
    const sol = readFileSync(join(__dirname, "..", "..", "components", "EnCoursView", "SolDeSalle.tsx"), "utf-8");
    expect(sol).toContain('motif="dalles"');
  });
});

describe("product agent sprites", () => {
  it("draws the agent, its console and the GPU rack from the sprite engine, with no Tailwind hue", () => {
    for (const nom of ["AgentAuPupitre", "PosteVide", "BaieGpu"]) {
      const contenu = source(nom);
      expect(contenu, nom).toContain("lib/bureau/sprites/produit");
      expect(contenu, nom).not.toMatch(/\b(?:fill|stroke|bg|text)-(?:zinc|red|amber|green|blue|violet)-\d/);
      expect(contenu, nom).not.toMatch(/anim-|animation|transition/);
    }
  });

  it("cuts the typing and the screen frames under reduced motion", () => {
    const reduit = CSS.slice(CSS.indexOf("@media (prefers-reduced-motion: reduce)"));
    expect(reduit).toMatch(/[.]anim-tape\b[^}]*animation:\s*none/);
    expect(reduit).toMatch(/[.]anim-trame\b[^}]*animation:\s*none/);
  });
});
