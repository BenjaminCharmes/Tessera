import { describe, it, expect } from "vitest";
import {
  classeDeLEtat,
  etatDuService,
  libelleDeLEtat,
} from "./etatDuService";
import type { ServiceActif } from "../types/api";

function service(over: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom: "dev",
    project_id: "fluentdb",
    pid: 1,
    demarre_a: new Date().toISOString(),
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

describe("etatDuService", () => {
  it("distingue un service arrete a la main d'un service qui a echoue", () => {
    // `terminate()` produit un code non nul sur certaines plateformes :
    // confondre les deux enverrait chercher des logs qui ne disent rien.
    expect(etatDuService(service({ en_cours: false, code_de_sortie: null })))
      .toBe("arrete");
    expect(etatDuService(service({ en_cours: false, code_de_sortie: 1 })))
      .toBe("echoue");
    expect(etatDuService(service())).toBe("en-cours");
  });

  it("nomme l'etat en francais, avec le code quand il y en a un", () => {
    expect(libelleDeLEtat(service())).toBe("en cours");
    expect(libelleDeLEtat(service({ en_cours: false, code_de_sortie: 3 })))
      .toContain("code 3");
    expect(libelleDeLEtat(service({ en_cours: false }))).toBe("à l'arrêt");
  });

  it("n'emprunte qu'aux familles d'etat d'ADR-026", () => {
    // Le violet est reserve a l'identite : un service n'en est pas un.
    const classes = [
      classeDeLEtat(service()),
      classeDeLEtat(service({ en_cours: false, code_de_sortie: 1 })),
      classeDeLEtat(service({ en_cours: false })),
    ];
    expect(classes.join(" ")).not.toMatch(/violet/);
    expect(classes[0]).toMatch(/blue/);
    expect(classes[1]).toMatch(/red/);
    expect(classes[2]).toMatch(/zinc/);
  });
});
