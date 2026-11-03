import { describe, expect, it } from "vitest";
import { TENUES, type Physique } from "../physique";
import type { Sprite } from "./grille";
import { bureauEnBois, canape, chaise, classeur, frigo, tableDeReunion } from "./communs";

function jetons(s: Sprite): Set<string> {
  return new Set(s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : []))));
}

const RH: Physique = { peau: 5, cheveux: 4, coiffure: "court", jupe: false };

describe("common rooms", () => {
  it("furnishes the rooms without any state tone nor animation (ADR-058)", () => {
    for (const s of [canape(), frigo(), classeur(), tableDeReunion(), chaise(), bureauEnBois(null)]) {
      expect([...jetons(s)].some((t) => t.startsWith("etat-"))).toBe(false);
      expect(s.calques.every((c) => c.classe === "")).toBe(true);
    }
  });

  it("seats the room figure at the wooden desk, with a tie for the director only", () => {
    const directeur = jetons(bureauEnBois({ tenue: TENUES.reviewer, physique: RH }));
    const rh = jetons(bureauEnBois({ tenue: TENUES.validateur, physique: RH }));
    expect(directeur).toContain("cravate.b");
    expect(rh).not.toContain("cravate.b");
    expect(rh).toContain("peau5.b");
  });

  it("leaves the armchair empty when the figure is away", () => {
    expect([...jetons(bureauEnBois(null))].some((t) => t.startsWith("peau"))).toBe(false);
  });

  it("pins a post-it on the fridge and a cushion on the sofa", () => {
    expect(jetons(frigo())).toContain("postit.b");
    expect(jetons(canape())).toContain("coussin.b");
  });
});
