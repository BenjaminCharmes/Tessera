import { describe, expect, it } from "vitest";
import { libelleDeLAttente, resteAvant } from "./attente";

const MAINTENANT = Date.parse("2026-09-25T09:00:00Z");

describe("resteAvant", () => {
  it("rend les millisecondes qui restent", () => {
    expect(resteAvant("2026-09-25T09:05:00Z", MAINTENANT)).toBe(300_000);
  });

  it("ne descend pas sous zéro une fois l'échéance passée", () => {
    expect(resteAvant("2026-09-25T08:59:00Z", MAINTENANT)).toBe(0);
  });

  it("ne promet rien sans échéance", () => {
    expect(resteAvant(null, MAINTENANT)).toBeNull();
  });

  it("ne promet rien d'une échéance illisible", () => {
    // Un backend plus ancien n'envoie pas ce champ ; un « NaN » à l'écran
    // serait pire que rien.
    expect(resteAvant("bientôt", MAINTENANT)).toBeNull();
  });
});

describe("libelleDeLAttente", () => {
  it("compte en minutes et secondes au-delà d'une minute", () => {
    expect(libelleDeLAttente(125_000)).toBe(
      "Sans réponse, l'agent reprend dans 2m 5s.",
    );
  });

  it("compte en secondes en dessous d'une minute", () => {
    expect(libelleDeLAttente(4_000)).toBe(
      "Sans réponse, l'agent reprend dans 4s.",
    );
  });

  it("dit que l'agent reprend une fois le délai écoulé", () => {
    expect(libelleDeLAttente(0)).toBe("L'agent reprend sur sa propre hypothèse.");
  });

  it("ne dit rien sans échéance", () => {
    expect(libelleDeLAttente(null)).toBeNull();
  });
});
