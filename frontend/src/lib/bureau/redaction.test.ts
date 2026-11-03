import { describe, expect, it } from "vitest";
import { BIBLIOTHEQUE_X, libelleActivite } from "./activites";
import { REDACTEURS, placerLesRedacteurs } from "./redaction";

describe("placerLesRedacteurs", () => {
  it("stands the two writers at the library while the documentation runs", () => {
    const redacteurs = placerLesRedacteurs(true);

    expect(redacteurs.map((r) => r.role)).toEqual(["doc-technique", "doc-fonctionnelle"]);
    for (const r of redacteurs) {
      expect(r).toMatchObject({ x: BIBLIOTHEQUE_X, niveau: "fond", activite: "redige", parti: false });
    }
    expect(libelleActivite("redige")).toBe("rédige la documentation");
  });

  it("keeps the two writers side by side, not on top of each other", () => {
    const [premier, second] = placerLesRedacteurs(true);

    expect(premier?.decalage).not.toBe(second?.decalage);
  });

  it("draws nobody outside the documentation", () => {
    expect(placerLesRedacteurs(false)).toEqual([]);
  });

  it("names exactly the two writers of the batch documentation", () => {
    expect([...REDACTEURS]).toEqual(["doc-technique", "doc-fonctionnelle"]);
  });
});
