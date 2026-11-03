import { describe, expect, it } from "vitest";
import { TENUES, type Physique } from "../physique";
import type { Sprite } from "./grille";
import { type OptionsDebout, PAS, debout, marche } from "./debout";

const AGENT: Physique = { peau: 2, cheveux: 4, coiffure: "long", jupe: false };

function jetons(s: Sprite): Set<string> {
  return new Set(s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : []))));
}

function de(o: Partial<OptionsDebout> = {}): Sprite {
  return debout({ physique: AGENT, tenue: TENUES.reviewer, expression: "fait", mains: "tasse", ...o });
}

describe("debout", () => {
  it("wears trousers, or a skirt with bare legs when the look has one", () => {
    expect(jetons(de())).toContain("pantalon.b");
    const jupe = jetons(de({ physique: { ...AGENT, jupe: true } }));
    expect(jupe).not.toContain("pantalon.b");
    expect(jupe).toContain("haut-reviewer.d");
  });

  it("holds a cup, a corrected sheet, or nothing", () => {
    expect(jetons(de())).toContain("tasse.b");
    const feuille = jetons(de({ mains: "feuille" }));
    expect(feuille).toContain("papier.b");
    expect(feuille).not.toContain("tasse.b");
    expect(jetons(de({ mains: "vides" }))).not.toContain("tasse.b");
  });

  it("raises both arms above the head to celebrate", () => {
    const g = de({ mains: "levees" }).calques[0]?.g;
    expect(g?.get(0, 2)).toMatch(/^peau2/);
    expect(g?.get(18, 2)).toMatch(/^peau2/);
  });

  it("is still: no animation on a standing agent", () => {
    expect(de().calques.every((c) => c.classe === "")).toBe(true);
  });
});

describe("marche", () => {
  it("plays the four steps frame by frame, the first one visible without animation", () => {
    const s = marche({ physique: AGENT, tenue: TENUES.codeur, expression: "neutre", mains: "vides" });
    expect(s.calques).toHaveLength(PAS.length);
    expect(s.calques.every((c) => c.classe.includes("anim-trame-4"))).toBe(true);
    expect(s.calques[0]?.style?.opacity).toBeUndefined();
    expect(s.calques.slice(1).every((c) => c.style?.opacity === "0")).toBe(true);
  });

  it("lifts a foot on the second step", () => {
    const s = marche({ physique: AGENT, tenue: TENUES.codeur, expression: "neutre", mains: "vides" });
    const pied = (k: number) => s.calques[k]?.g.get(4, 39);
    expect(pied(0)).toMatch(/^chaussure/);
    expect(pied(1)).toBeNull();
  });
});
