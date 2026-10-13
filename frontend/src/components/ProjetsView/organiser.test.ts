import { describe, expect, it } from "vitest";
import type { ProjectOverview } from "../../types/api";
import {
  FILTRES_PAR_DEFAUT,
  SANS_CATEGORIE,
  estFiltresProjets,
  filtrerProjets,
  filtresActifs,
  normaliser,
  pastillesDeCategories,
  trierProjets,
} from "./organiser";

function vue(id: string, extra: Partial<ProjectOverview> = {}): ProjectOverview {
  return {
    id,
    name: id,
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-09-01T00:00:00Z",
    last_activity: null,
    tickets: { todo: 0, in_progress: 0, in_review: 0, blocked: 0, done: 0 },
    run_actif: false,
    icon: false,
    services_declares: false,
    services_en_cours: false,
    ...extra,
  };
}

describe("normaliser", () => {
  it("lowercases and strips accents", () => {
    expect(normaliser("Démineur ÉLAN")).toBe("demineur elan");
  });
});

describe("filtrerProjets", () => {
  const projets = [
    vue("demineur", { name: "Démineur", category: "Jeux", description: "Mines" }),
    vue("ide-core", { description: "Un IDE de bureau" }),
  ];

  it("searches name, id and description", () => {
    const cherche = (recherche: string) =>
      filtrerProjets(projets, { ...FILTRES_PAR_DEFAUT, recherche }).map((p) => p.id);
    expect(cherche("DEMINÉUR")).toEqual(["demineur"]);
    expect(cherche("ide-")).toEqual(["ide-core"]);
    expect(cherche("bureau")).toEqual(["ide-core"]);
  });

  it("filters by category, including projects without one", () => {
    const par = (categorie: string) =>
      filtrerProjets(projets, { ...FILTRES_PAR_DEFAUT, categorie }).map((p) => p.id);
    expect(par("Jeux")).toEqual(["demineur"]);
    expect(par(SANS_CATEGORIE)).toEqual(["ide-core"]);
  });
});

describe("trierProjets", () => {
  const a = vue("a", { last_activity: "2026-10-01T00:00:00Z", created_at: "2026-01-01T00:00:00Z" });
  const b = vue("b", { last_activity: "2026-10-05T00:00:00Z", created_at: "2026-02-01T00:00:00Z" });
  const c = vue("c", { last_activity: null, created_at: "2026-03-01T00:00:00Z" });

  it("sorts by name, recent activity (none last) and recent creation", () => {
    const ids = (tri: "nom" | "activite" | "creation") =>
      trierProjets([c, a, b], tri).map((p) => p.id);
    expect(ids("nom")).toEqual(["a", "b", "c"]);
    expect(ids("activite")).toEqual(["b", "a", "c"]);
    expect(ids("creation")).toEqual(["c", "b", "a"]);
  });

  it("does not mutate its input", () => {
    const entree = [b, a];
    trierProjets(entree, "nom");
    expect(entree).toEqual([b, a]);
  });
});

describe("pastillesDeCategories", () => {
  it("counts per category, named ones alphabetically then the uncategorised", () => {
    const pastilles = pastillesDeCategories([
      vue("1", { category: "Outils" }),
      vue("2", { category: "Jeux" }),
      vue("3"),
      vue("4", { category: "Jeux" }),
    ]);
    expect(pastilles).toEqual([
      { valeur: "Jeux", libelle: "Jeux", nombre: 2 },
      { valeur: "Outils", libelle: "Outils", nombre: 1 },
      { valeur: SANS_CATEGORIE, libelle: "Sans catégorie", nombre: 1 },
    ]);
  });
});

describe("filtresActifs and estFiltresProjets", () => {
  it("tells whether a search or a category narrows the list", () => {
    expect(filtresActifs(FILTRES_PAR_DEFAUT)).toBe(false);
    expect(filtresActifs({ ...FILTRES_PAR_DEFAUT, recherche: " x " })).toBe(true);
    expect(filtresActifs({ ...FILTRES_PAR_DEFAUT, categorie: "Jeux" })).toBe(true);
  });

  it("rejects a stored value that is not a filter set", () => {
    expect(estFiltresProjets(FILTRES_PAR_DEFAUT)).toBe(true);
    expect(estFiltresProjets({ recherche: 3, categorie: null, tri: "nom" })).toBe(false);
    expect(estFiltresProjets({ recherche: "", categorie: null, tri: "autre" })).toBe(false);
    expect(estFiltresProjets(null)).toBe(false);
  });
});
