import { describe, expect, it, vi } from "vitest";
import { servicesDeLaBaie } from "./servicesDeLaBaie";
import type { UseServicesResult } from "../../hooks/useServices";

const eteints: UseServicesResult = {
  services: [
    {
      nom: "backend",
      project_id: "ide-core",
      pid: null,
      demarre_a: "2026-10-28T10:00:00Z",
      en_cours: false,
      code_de_sortie: null,
    },
  ],
  enCours: false,
  enEchec: false,
  declare: true,
  erreur: null,
  demarrer: vi.fn(),
  arreter: vi.fn(),
  rafraichir: vi.fn(),
};

describe("servicesDeLaBaie", () => {
  it("shows the servers of the project that runs the IDE as running", () => {
    const baie = servicesDeLaBaie(eteints, true);

    expect(baie.enCours).toBe(true);
    expect(baie.services.every((s) => s.en_cours)).toBe(true);
  });

  it("leaves any other project's services as the registry reads them", () => {
    expect(servicesDeLaBaie(eteints, false)).toBe(eteints);
  });
});
