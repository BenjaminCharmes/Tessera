import { describe, expect, it } from "vitest";
import { TENUES, type Physique } from "../physique";
import { type Sprite, sprite } from "./grille";
import { type OptionsPoste, poste, tete, torseDetails } from "./poste";

const AGENT: Physique = { peau: 3, cheveux: 2, coiffure: "court", jupe: false };

/** Les jetons nus d'un sprite, sans marque de liseré ni de lueur. */
function jetons(s: Sprite): Set<string> {
  return new Set(s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [(c.split("^")[0] ?? c).replace("~r", "")] : []))));
}

function posteDe(o: Partial<OptionsPoste> = {}): Sprite {
  return poste({ physique: AGENT, tenue: TENUES.codeur, vide: false, expression: "actif", tape: true, etatEcran: "actif", scene: false, ...o });
}

describe("tete", () => {
  it("keeps a 12-pixel face, below the eyes, whatever the haircut", () => {
    for (const coiffure of ["court", "long", "carre", "chauve"] as const) {
      const g = sprite(24, 24).calque();
      tete(g, 6, 6, { ...AGENT, coiffure });
      const visage = [...Array(24).keys()].filter((x) => g.get(x, 12)?.startsWith("peau3"));
      expect(visage.length, coiffure).toBeGreaterThanOrEqual(12);
    }
  });

  it("lets long hair fall lower than the bob", () => {
    const bas = (coiffure: "long" | "carre") => {
      const g = sprite(24, 24).calque();
      tete(g, 6, 6, { ...AGENT, coiffure });
      return Math.max(...[...Array(24).keys()].filter((y) => g.get(4, y)?.startsWith("cheveux")));
    };
    expect(bas("long")).toBeGreaterThan(bas("carre"));
  });

  it("follows the agent's health in the face: sweat only when it looks frozen", () => {
    const sueur = (expr: "blocage" | "actif") => {
      const g = sprite(24, 24).calque();
      tete(g, 4, 6, AGENT, expr);
      return g.p.some((c) => c?.startsWith("sueur"));
    };
    expect(sueur("blocage")).toBe(true);
    expect(sueur("actif")).toBe(false);
  });
});

describe("torseDetails", () => {
  it("draws a tie on the reviewer, a hood on the coder, and neither on the others", () => {
    const details = (role: keyof typeof TENUES) => {
      const g = sprite(24, 24).calque();
      torseDetails(g, TENUES[role], 4, 4);
      return new Set(g.p.filter(Boolean));
    };
    expect(details("reviewer")).toContain("cravate.b");
    expect(details("codeur")).toContain("haut-codeur.d");
    expect(details("testeur").size).toBe(0);
  });
});

describe("poste", () => {
  it("types only when told to, and only with someone seated", () => {
    expect(posteDe().calques.some((c) => c.classe === "anim-tape")).toBe(true);
    expect(posteDe({ tape: false }).calques.some((c) => c.classe === "anim-tape")).toBe(false);
    expect(posteDe({ vide: true }).calques.some((c) => c.classe === "anim-tape")).toBe(false);
  });

  it("tints the screen with the state only, in its own tokens", () => {
    expect(jetons(posteDe({ etatEcran: "question" }))).toContain("etat-question.hi");
    expect([...jetons(posteDe({ vide: true }))].some((t) => t.startsWith("etat-"))).toBe(false);
  });

  it("never outlines a state token", () => {
    expect([...jetons(posteDe({ etatEcran: "blocage" }))].filter((t) => t.startsWith("etat-") && t.endsWith(".ol"))).toEqual([]);
  });

  it("glows the seated agent with the screen hue at night", () => {
    const marques = posteDe({ etatEcran: "fait" }).calques[1]?.g.p.filter((c) => c?.includes("^fait^")) ?? [];
    expect(marques.length).toBeGreaterThan(0);
  });
});
