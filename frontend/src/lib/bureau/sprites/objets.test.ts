import { describe, expect, it } from "vitest";
import type { Sprite } from "./grille";
import { boite, confetti, corbeille, dossier, gyrophare, imprimante, vapeur } from "./objets";

function jetons(s: Sprite): string[] {
  return s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : [])));
}

const etats = (s: Sprite) => jetons(s).filter((t) => t.startsWith("etat-"));
const classes = (s: Sprite) => s.calques.map((c) => c.classe).filter(Boolean);

describe("run room objects", () => {
  it("keeps the printer and the folder as furniture: no state, no animation", () => {
    for (const s of [imprimante(), dossier()]) {
      expect(etats(s)).toEqual([]);
      expect(classes(s)).toEqual([]);
    }
  });

  it("fills the bin with one paper ball per refusal, three at most", () => {
    const papier = (n: 0 | 1 | 2 | 3) => jetons(corbeille(n)).filter((t) => t.startsWith("papier.")).length;
    expect(papier(0)).toBe(0);
    expect(papier(2)).toBeGreaterThan(papier(1));
    expect(papier(3)).toBeGreaterThan(papier(2));
  });

  it("raises the mailbox flag in the tone of the pull request, and nothing without one", () => {
    expect(etats(boite("aucune"))).toEqual([]);
    expect(jetons(boite("aucune"))).not.toContain("papier.b");
    expect(etats(boite("ouverte")).every((t) => t.startsWith("etat-question"))).toBe(true);
    expect(etats(boite("ci")).every((t) => t.startsWith("etat-actif"))).toBe(true);
    expect(etats(boite("mergee")).every((t) => t.startsWith("etat-fait"))).toBe(true);
    expect(etats(boite("refusee")).every((t) => t.startsWith("etat-blocage"))).toBe(true);
  });

  it("blinks the beacon dome in the blocked tone, on a still base", () => {
    const s = gyrophare();
    expect(classes(s)).toEqual(["anim-gyro"]);
    expect(etats(s).every((t) => t.startsWith("etat-blocage"))).toBe(true);
  });

  it("lifts three plumes of steam, each at its own pace", () => {
    const s = vapeur();
    expect(classes(s)).toEqual(["anim-vapeur", "anim-vapeur", "anim-vapeur"]);
    expect(new Set(s.calques.map((c) => c.style?.animationDelay)).size).toBe(3);
  });

  it("cuts five confetti shapes in five tones", () => {
    const tons = new Set([0, 1, 2, 3, 4].map((i) => jetons(confetti(i)).find((t) => t.endsWith(".b"))));
    expect(tons.size).toBe(5);
  });
});
