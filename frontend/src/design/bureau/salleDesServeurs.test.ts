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

describe("product agent sprites", () => {
  const SPRITES_AGENT = ["Console", "AgentAuPupitre"];

  it("reads every tone from a --sprite-* token defined in index.css, with no state hue", () => {
    for (const nom of SPRITES_AGENT) {
      const contenu = source(nom);
      expect(contenu, nom).toContain("--sprite-");
      expect(contenu, nom).not.toMatch(/\b(?:fill|stroke|bg|text)-(?:red|amber|green|blue|violet)-\d/);
      expect(contenu, nom).not.toMatch(/#[0-9a-fA-F]{3,8}\b|\brgba?\(|\bhsla?\(|\boklch\(/);
      for (const m of contenu.matchAll(/--sprite-([a-z0-9-]+)/g)) {
        expect(CSS, `${nom}: --sprite-${m[1]}`).toMatch(new RegExp(`--sprite-${m[1]}:`));
      }
    }
  });

  it("keeps the console still, and moves an agent only with the typing animation that reduced motion cuts", () => {
    expect(source("Console")).not.toMatch(/anim-|animation|transition|data-voyant/);
    const agent = source("AgentAuPupitre");
    expect([...new Set(agent.match(/anim-[a-z]+/g))]).toEqual(["anim-tape"]);
    expect(agent).not.toMatch(/animation|transition/);
    const reduit = CSS.slice(CSS.indexOf("@media (prefers-reduced-motion: reduce)"));
    expect(reduit).toMatch(/[.]anim-tape\b[^}]*animation:\s*none/);
  });
});
