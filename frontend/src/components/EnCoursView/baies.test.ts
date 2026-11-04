import { describe, expect, it } from "vitest";
import type { AppEnCours, ServiceActif } from "../../types/api";
import { baiesDuProjet } from "./baies";

function app(nom: string, origine: AppEnCours["origine"]): AppEnCours {
  return {
    project_id: "demo",
    project_name: "Demo",
    nom,
    origine,
    pid: 4242,
    ports: [8025],
    demarre_a: null,
    memoire_mo: 120,
  };
}

function service(nom: string, surcharge: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom,
    project_id: "demo",
    pid: null,
    demarre_a: "",
    en_cours: false,
    code_de_sortie: null,
    sortie: [],
    arrete_a_la_main: false,
    ...surcharge,
  };
}

describe("baiesDuProjet", () => {
  it("shows a declared service started by hand as running", () => {
    const baies = baiesDuProjet([app("api", "externe")], [service("api")]);
    expect(baies).toEqual([{ nom: "api", etat: "en-cours", libelle: "lancé à la main" }]);
  });

  it("keeps a declared service without a matching app as never launched", () => {
    const baies = baiesDuProjet([app("worker", "externe")], [service("api")]);
    expect(baies[0]).toEqual({
      nom: "api",
      etat: "jamais-lance",
      libelle: "pas lancé par l'IDE",
    });
  });

  it("keeps the state and label of a service the IDE launched", () => {
    const lance = service("api", { pid: 4242, en_cours: true });
    const baies = baiesDuProjet([app("api", "tessera")], [lance]);
    expect(baies).toEqual([{ nom: "api", etat: "en-cours", libelle: "en cours" }]);
  });

  it("still adds a bay for an app no declared service names", () => {
    const baies = baiesDuProjet([app("vigie", "externe")], []);
    expect(baies).toEqual([{ nom: "vigie", etat: "en-cours", libelle: "en cours" }]);
  });
});
