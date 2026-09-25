import { describe, expect, it } from "vitest";
import { lienDuDepot } from "./lienDuDepot";

describe("lienDuDepot", () => {
  it("fait une URL GitHub d'un owner/repo", () => {
    expect(lienDuDepot("BenjaminCharmes/demineur")).toBe(
      "https://github.com/BenjaminCharmes/demineur",
    );
  });

  it("garde une URL https en retirant son .git", () => {
    expect(lienDuDepot("https://github.com/moi/mon-repo.git")).toBe(
      "https://github.com/moi/mon-repo",
    );
  });

  it("garde l'hôte d'une adresse SSH", () => {
    expect(lienDuDepot("git@gitlab.com:moi/mon-repo.git")).toBe(
      "https://gitlab.com/moi/mon-repo",
    );
  });

  it("garde un chemin SSH à plus de deux segments", () => {
    expect(lienDuDepot("git@gitlab.com:groupe/sous-groupe/repo.git")).toBe(
      "https://gitlab.com/groupe/sous-groupe/repo",
    );
  });

  it("ignore les espaces autour de la valeur", () => {
    expect(lienDuDepot("  moi/repo  ")).toBe("https://github.com/moi/repo");
  });

  it("ne rend rien d'une valeur absente ou vide", () => {
    expect(lienDuDepot(null)).toBeNull();
    expect(lienDuDepot(undefined)).toBeNull();
    expect(lienDuDepot("   ")).toBeNull();
  });

  it("ne rend rien d'un chemin local", () => {
    // Un dépôt cloné depuis un disque n'a pas de page à ouvrir.
    expect(lienDuDepot("/home/moi/depots/mon-repo")).toBeNull();
    expect(lienDuDepot("../voisin")).toBeNull();
  });
});
