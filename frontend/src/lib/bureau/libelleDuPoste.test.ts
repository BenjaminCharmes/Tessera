import { describe, expect, it } from "vitest";
import { libelleDuPoste, nomDuPoste } from "./libelleDuPoste";

describe("libelleDuPoste", () => {
  it("says the health of a busy post", () => {
    expect(libelleDuPoste("codeur", "occupe", "actif")).toBe("Codeur, travaille");
    expect(libelleDuPoste("validateur", "occupe", "question")).toBe("Validateur, question");
    expect(libelleDuPoste("reviewer", "occupe", "blocage_suspecte")).toBe("Reviewer, figé ?");
  });

  it("ignores the health of a post that is not busy", () => {
    expect(libelleDuPoste("testeur", "fait", "blocage_suspecte")).toBe("Testeur, a fini");
    expect(libelleDuPoste("securite", "libre", "question")).toBe("Sécurité, attend son tour");
  });

  it("calls a free post of a room without run simply free", () => {
    expect(libelleDuPoste("securite", "libre", "attente", true)).toBe("Sécurité, libre");
  });

  it("names every post", () => {
    expect(nomDuPoste("securite")).toBe("Sécurité");
    expect(nomDuPoste("codeur")).toBe("Codeur");
    expect(nomDuPoste("architect")).toBe("Architecte");
  });
});
