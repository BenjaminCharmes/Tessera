import { describe, expect, it } from "vitest";
import type { Sprite } from "./grille";
import { fenetre, horloge, interrupteur, plafonnier, porte } from "./mur";

function jetons(s: Sprite): Set<string> {
  return new Set(s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : []))));
}

describe("wall", () => {
  it("shows a day sky with sun and clouds, or a night sky with stars that twinkle", () => {
    const jour = fenetre({ jour: true, soleil: true, nuages: 2 });
    expect(jetons(jour)).toContain("soleil.b");
    expect(jetons(jour)).toContain("nuage.b");
    expect(jour.calques.every((c) => c.classe === "")).toBe(true);
    const nuit = fenetre({ jour: false, soleil: false, nuages: 0 });
    expect(jetons(nuit)).toContain("ciel-nuit.b");
    expect(jetons(nuit)).not.toContain("soleil.b");
    expect(nuit.calques.filter((c) => c.classe === "anim-scintille")).toHaveLength(2);
  });

  it("lights the lamp diffuser only when switched on", () => {
    expect(jetons(plafonnier(true))).toContain("lampe.b");
    expect(jetons(plafonnier(false))).not.toContain("lampe.b");
  });

  it("moves the hands with the hour of the view clock", () => {
    const aiguilles = (h: number, m: number) => horloge(h, m).calques[2]?.g.p.map((c) => (c ? 1 : 0)).join("");
    expect(aiguilles(3, 0)).not.toBe(aiguilles(9, 0));
    expect(aiguilles(15, 0)).toBe(aiguilles(3, 0));
  });

  it("presses the switch rocker on the off side", () => {
    expect(interrupteur(true).calques[0]?.g.get(5, 5)).toMatch(/^interrupteur\.(b|hi)/);
    expect(interrupteur(false).calques[0]?.g.get(5, 5)).toMatch(/^interrupteur\.s/);
  });

  it("keeps the door as furniture, with no state", () => {
    expect([...jetons(porte())].some((t) => t.startsWith("etat-"))).toBe(false);
  });
});
