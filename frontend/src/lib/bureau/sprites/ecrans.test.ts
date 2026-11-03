import { describe, expect, it } from "vitest";
import type { EcranId } from "../ecranDuPoste";
import type { Sprite } from "./grille";
import { scene } from "./ecrans";

function classes(s: Sprite | null): string[] {
  return (s?.calques ?? []).flatMap((c) => c.classe.split(" ").filter(Boolean));
}

function jetons(s: Sprite | null): Set<string> {
  return new Set((s?.calques ?? []).flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : []))));
}

/**
 * L'instant où chaque image d'une animation image par image devient visible : la
 * keyframe montre l'image sur le premier 1/n du cycle, un délai négatif l'avance d'autant.
 */
function debutsDesImages(s: Sprite): number[] {
  return s.calques
    .filter((c) => c.classe.includes("anim-trame"))
    .map(({ style }) => {
      const duree = parseFloat(style?.animationDuration ?? "0");
      const avance = -parseFloat(style?.animationDelay ?? "0");
      return +((((duree - avance) % duree) + duree) % duree).toFixed(3);
    });
}

describe("scene", () => {
  it("draws nothing for a lit or a dark screen without scene", () => {
    expect(scene("allume", "actif", true)).toBeNull();
    expect(scene("eteint", "actif", false)).toBeNull();
  });

  it("plays the moving scenes only when the agent really works", () => {
    for (const [ecran, classe] of [
      ["code", "anim-trame-8"],
      ["tests", "anim-trame-6"],
      ["audit", "anim-trame-8"],
      ["diff", "anim-lueur"],
      ["criteres", "anim-lueur"],
    ] as const) {
      expect(classes(scene(ecran, "actif", true)), ecran).toContain(classe);
      expect(classes(scene(ecran, "attente", false)), ecran).toEqual([]);
    }
  });

  it("never animates the page, the tick or the cross", () => {
    for (const ecran of ["lecture", "ok", "ko"] as EcranId[]) expect(classes(scene(ecran, "actif", true)), ecran).toEqual([]);
  });

  it("draws the diff in green and red, the verdicts in their own tone, the rest in the run's", () => {
    const diff = jetons(scene("diff", "actif", false));
    expect(diff).toContain("etat-fait.b");
    expect(diff).toContain("etat-blocage.b");
    expect(jetons(scene("ok", "actif", false))).toContain("etat-fait.b");
    expect(jetons(scene("ko", "actif", false))).toContain("etat-blocage.b");
    expect(jetons(scene("code", "question", false))).toContain("etat-question.b");
  });

  it("plays its frames in order: the test bar fills, the code scrolls forward", () => {
    for (const ecran of ["code", "tests", "audit"] as const) {
      const debuts = debutsDesImages(scene(ecran, "actif", true) as Sprite);
      expect(debuts[0], ecran).toBe(0);
      expect(debuts, ecran).toEqual([...debuts].sort((a, b) => a - b));
      expect(new Set(debuts).size, ecran).toBe(debuts.length);
    }
  });
});
