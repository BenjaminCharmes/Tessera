import { describe, it, expect } from "vitest";
import { grouperParCategorie } from "./grouperParCategorie";
import type { Project } from "../../types/api";

function projet(id: string, category: string | null = null): Project {
  return {
    id,
    name: id,
    path: `/w/${id}`,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
    category,
  };
}

describe("grouperParCategorie (ticket-175)", () => {
  it("regroupe les projets d'une même catégorie", () => {
    const groupes = grouperParCategorie([
      projet("a", "Pro"),
      projet("b", "Perso"),
      projet("c", "Pro"),
    ]);

    const pro = groupes.find((g) => g.categorie === "Pro");
    expect(pro?.projets.map((p) => p.id)).toEqual(["a", "c"]);
  });

  it("ordonne les catégories alphabétiquement, pas par apparition", () => {
    // L'ordre d'apparition change dès qu'on ajoute un projet.
    const groupes = grouperParCategorie([projet("a", "Pro"), projet("b", "Perso")]);

    expect(groupes.map((g) => g.categorie)).toEqual(["Perso", "Pro"]);
  });

  it("met les projets sans catégorie en dernier", () => {
    const groupes = grouperParCategorie([projet("a"), projet("b", "Pro")]);

    expect(groupes.map((g) => g.categorie)).toEqual(["Pro", null]);
  });

  it("ne perd aucun projet", () => {
    const entree = [projet("a", "Pro"), projet("b"), projet("c", "Perso")];

    const total = grouperParCategorie(entree).flatMap((g) => g.projets);

    expect(total).toHaveLength(3);
  });

  it("une catégorie qui n'est que des espaces vaut pas de catégorie", () => {
    const groupes = grouperParCategorie([projet("a", "   ")]);

    expect(groupes).toEqual([{ categorie: null, projets: [projet("a", "   ")] }]);
  });

  it("sans projet, aucun groupe", () => {
    expect(grouperParCategorie([])).toEqual([]);
  });
});
