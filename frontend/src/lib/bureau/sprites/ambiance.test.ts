import { describe, expect, it } from "vitest";
import { HAUTEUR_DE_LA_PLINTHE, contenuDuMotif, murEnduit, plinthe, solParquet } from "./ambiance";

const jetons = (s: ReturnType<typeof solParquet>) => new Set(s.calques.flatMap(({ g }) => g.p.filter(Boolean)));

describe("ambiance tiles", () => {
  it("lays the parquet in four tones of the floor family", () => {
    expect([...jetons(solParquet())].sort()).toEqual(["sol.b", "sol.d", "sol.hi", "sol.s"]);
  });

  it("fills the whole wall tile, sparsely grained, in the family asked", () => {
    const mur = murEnduit("salle-mur");
    expect(mur.calques[0]?.g.p.every(Boolean)).toBe(true);
    expect(jetons(mur)).toEqual(new Set(["salle-mur.b", "salle-mur.hi", "salle-mur.s"]));
    const grain = mur.calques[0]?.g.p.filter((t) => t !== "salle-mur.b").length ?? 0;
    expect(grain).toBeGreaterThan(0);
    expect(grain).toBeLessThan(32 * 32 * 0.1);
  });

  it("lights the top edge of the skirting board", () => {
    const g = plinthe().calques[0]?.g;
    expect(g?.get(3, 0)).toBe("plinthe.hi");
    expect(g?.get(3, 5)).toBe("plinthe.d");
  });

  it("gives each pattern one id per moment, sized on screen, without outline or rim", () => {
    const jour = contenuDuMotif("sol", "jour");
    const nuit = contenuDuMotif("sol", "nuit");
    expect(jour.id).toBe("tuile-sol-jour");
    expect(nuit.tuile?.moment).toBe("nuit");
    expect(jour.tuile).toMatchObject({ largeur: 112, hauteur: 21 });
    expect(jour.chemins.every((c) => !c.fill.includes("lisere") && !c.fill.endsWith("-ol)"))).toBe(true);
    expect(contenuDuMotif("sol", "jour")).toBe(jour);
    expect(HAUTEUR_DE_LA_PLINTHE).toBe(10.5);
  });
});
