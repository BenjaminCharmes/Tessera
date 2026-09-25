import { describe, expect, it } from "vitest";
import { abonnementsVoulus, diffDesAbonnements } from "./abonnements";

describe("abonnementsVoulus", () => {
  it("ne garde qu'une fois un run que les deux slots demandent", () => {
    const voulus = abonnementsVoulus({ selection: "run-a", panneau: "run-a" });

    expect([...voulus]).toEqual(["run-a"]);
  });

  it("garde les deux runs quand ils diffèrent", () => {
    const voulus = abonnementsVoulus({ selection: "run-a", panneau: "run-b" });

    expect([...voulus].sort()).toEqual(["run-a", "run-b"]);
  });

  it("ignore un slot vide", () => {
    expect([...abonnementsVoulus({ selection: null, panneau: null })]).toEqual(
      [],
    );
  });
});

describe("diffDesAbonnements", () => {
  it("abonne le run que le panneau vient d'afficher", () => {
    const diff = diffDesAbonnements(new Set(), new Set(["run-a"]));

    expect(diff).toEqual({ ajouts: ["run-a"], retraits: [] });
  });

  it("ne réabonne pas un run déjà en vigueur", () => {
    const diff = diffDesAbonnements(new Set(["run-a"]), new Set(["run-a"]));

    expect(diff).toEqual({ ajouts: [], retraits: [] });
  });

  it("ne désabonne pas un run que l'autre slot regarde encore", () => {
    // La sélection passe de run-a à run-b pendant que le panneau montre run-a.
    const actuels = new Set(["run-a"]);
    const voulus = abonnementsVoulus({ selection: "run-b", panneau: "run-a" });

    expect(diffDesAbonnements(actuels, voulus)).toEqual({
      ajouts: ["run-b"],
      retraits: [],
    });
  });

  it("désabonne un run que plus personne ne regarde", () => {
    const diff = diffDesAbonnements(new Set(["run-a"]), new Set(["run-b"]));

    expect(diff).toEqual({ ajouts: ["run-b"], retraits: ["run-a"] });
  });
});
