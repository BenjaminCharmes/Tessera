import { describe, expect, it } from "vitest";
import { libelleCourtDeLaBoite, libelleDeLaBoite } from "./libelleDeLaBoite";

describe("libelleDeLaBoite", () => {
  it("drops the prefix in the short label", () => {
    expect(libelleCourtDeLaBoite({ etat: "aucune", pr: null })).toBe("aucune PR");
    expect(libelleCourtDeLaBoite({ etat: "ci", pr: 12 })).toBe("PR #12 CI en attente");
  });

  it("keeps the short label as the end of the long one", () => {
    const boite = { etat: "mergee", pr: 7 } as const;

    expect(libelleDeLaBoite(boite)).toBe(`Boîte aux lettres, ${libelleCourtDeLaBoite(boite)}`);
  });

  it("names a pull request without a number", () => {
    expect(libelleCourtDeLaBoite({ etat: "ouverte", pr: null })).toBe("PR ouverte");
  });
});
