import { describe, expect, it } from "vitest";
import { type Sprite, sprite } from "./grille";
import { bibliotheque, etagere, feuillage, machineACafe, meubleBas, plante, pot } from "./mobilier";

function jetons(s: Sprite): Set<string> {
  return new Set(s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : []))));
}

const MEUBLES: [string, Sprite][] = [
  ["pot", plante("pot")],
  ["cactus", plante("cactus")],
  ["ficus", plante("ficus")],
  ["machine", machineACafe()],
  ["meuble bas", meubleBas()],
  ["bibliotheque", bibliotheque()],
  ["etagere", etagere()],
];

describe("furniture", () => {
  it("never carries a state tone nor an animation (ADR-058)", () => {
    for (const [nom, s] of MEUBLES) {
      expect([...jetons(s)].some((t) => t.startsWith("etat-")), nom).toBe(false);
      expect(s.calques.every((c) => c.classe === ""), nom).toBe(true);
    }
  });

  it("grows a ficus taller than the potted plant and the cactus", () => {
    expect(plante("ficus").h).toBeGreaterThan(plante("pot").h);
    expect(jetons(plante("cactus"))).toContain("fleur.b");
  });

  it("shades foliage tufts and tapers a pot with soil on top", () => {
    const g = sprite(16, 16).calque();
    feuillage(g, "plante", [[8, 8, 4]]);
    expect(new Set(g.p.filter(Boolean))).toEqual(new Set(["plante.hi", "plante.b", "plante.s", "plante.d"]));
    const p = sprite(16, 16).calque();
    pot(p, "pot", 2, 2, 12, 6);
    expect(p.get(5, 2)).toBe("terre.b");
    expect(p.get(2, 8)).toBeNull();
  });

  it("puts a full cup in the coffee machine and books in the bookcase", () => {
    expect(jetons(machineACafe())).toContain("cafe.b");
    for (const livre of ["livre1.b", "livre2.b", "livre3.b"]) expect(jetons(bibliotheque())).toContain(livre);
  });
});
