import { describe, expect, it } from "vitest";
import type { Physique } from "../physique";
import type { Sprite } from "./grille";
import { CASES_MAX, cadre, cadreDore, tableauBlanc } from "./tableau";

function jetons(s: Sprite): string[] {
  return s.calques.flatMap(({ g }) => g.p.flatMap((c) => (c ? [c.replace("~r", "")] : [])));
}
const etats = (s: Sprite) => new Set(jetons(s).filter((t) => t.startsWith("etat-")).map((t) => t.split(".")[0]));

describe("tableauBlanc", () => {
  it("draws a grey box before judgement, a green tick when it passes, a red cross when it fails", () => {
    expect(etats(tableauBlanc(["attente"]))).toEqual(new Set(["etat-attente"]));
    expect(etats(tableauBlanc(["passe"]))).toEqual(new Set(["etat-fait"]));
    expect(etats(tableauBlanc(["echoue"]))).toEqual(new Set(["etat-blocage"]));
  });

  it("stays blank without criteria", () => {
    expect(etats(tableauBlanc([])).size).toBe(0);
  });

  it("writes twelve lines at most, all above the marker ledge", () => {
    const plein = tableauBlanc(Array.from({ length: 20 }, () => "passe" as const));
    const lignes = plein.calques[1]?.g;
    const ys = [...Array(54).keys()].filter((y) => [...Array(88).keys()].some((x) => lignes?.get(x, y)?.startsWith("etat-")));
    expect(Math.max(...ys)).toBeLessThan(47);
    expect(CASES_MAX).toBe(12);
  });
});

describe("cadres", () => {
  it("varies only the canvas of the wooden frame", () => {
    const toiles = [0, 1, 2, 3].map((i) => jetons(cadre(i as 0 | 1 | 2 | 3)).join());
    expect(new Set(toiles).size).toBe(4);
  });

  it("frames the coder of the project on velvet in gold", () => {
    const ph: Physique = { peau: 4, cheveux: 1, coiffure: "chauve", jupe: false };
    const t = new Set(jetons(cadreDore(ph)));
    expect(t).toContain("dore.b");
    expect(t).toContain("peau4.b");
    expect(t).toContain("haut-codeur.b");
  });
});
