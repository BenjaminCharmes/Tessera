import { describe, expect, it } from "vitest";
import { libelleDuPoste, nomDuPoste } from "./libelleDuPoste";

describe("libelleDuPoste", () => {
  it("says the health of a busy post", () => {
    expect(libelleDuPoste("codeur", "occupe", "actif")).toBe("Codeur, travaille");
    expect(libelleDuPoste("validateur", "occupe", "question")).toBe("Validateur, question");
    expect(libelleDuPoste("reviewer", "occupe", "blocage_suspecte")).toBe("Reviewer, figé ?");
  });

  it("ignores the health of a post that is not busy", () => {
    expect(libelleDuPoste("testeur", "fait", "blocage_suspecte")).toBe("Testeur, fait");
    expect(libelleDuPoste("securite", "libre", "question")).toBe("Sécurité, libre");
  });

  it("names every post", () => {
    expect(nomDuPoste("securite")).toBe("Sécurité");
    expect(nomDuPoste("codeur")).toBe("Codeur");
  });
});
