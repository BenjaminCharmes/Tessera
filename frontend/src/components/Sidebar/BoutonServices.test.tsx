import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BoutonServices from "./BoutonServices";
import type { UseServicesResult } from "../../hooks/useServices";
import type { ServiceActif } from "../../types/api";

function service(over: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom: "api",
    project_id: "ide-core",
    pid: 4242,
    demarre_a: new Date().toISOString(),
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

function etat(over: Partial<UseServicesResult> = {}): UseServicesResult {
  return {
    services: [],
    enCours: false,
    enEchec: false,
    declare: true,
    erreur: null,
    demarrer: vi.fn(),
    arreter: vi.fn(),
    rafraichir: vi.fn(),
    ...over,
  };
}

describe("BoutonServices", () => {
  it("n'apparait pas quand le projet ne declare aucun service", () => {
    // ADR-042 : ne rien declarer *est* la reponse « ce projet ne se lance pas
    // depuis l'IDE ». Un bouton desactive sans explication ferait chercher
    // une panne qui n'existe pas.
    render(
      <BoutonServices
        services={etat({ declare: false })}
        libelleDuProjet="carriere"
      />,
    );

    expect(screen.queryByRole("button")).not.toBeInTheDocument();
  });

  it("propose de lancer, puis d'arreter", async () => {
    const demarrer = vi.fn();
    const { rerender } = render(
      <BoutonServices services={etat({ demarrer })} libelleDuProjet="ide-core" />,
    );

    await userEvent.click(screen.getByRole("button", { name: /Lancer/ }));
    expect(demarrer).toHaveBeenCalled();

    rerender(
      <BoutonServices
        services={etat({ enCours: true, services: [service()] })}
        libelleDuProjet="ide-core"
      />,
    );
    expect(
      screen.getByRole("button", { name: /Arrêter/ }),
    ).toBeInTheDocument();
  });

  it("passe au rouge et propose de relancer apres un echec", () => {
    // Un service qui meurt de lui-meme doit se voir : c'est le cas ou l'on va
    // chercher les logs.
    render(
      <BoutonServices
        services={etat({
          enEchec: true,
          services: [service({ en_cours: false, code_de_sortie: 1 })],
        })}
        libelleDuProjet="ide-core"
      />,
    );

    const bouton = screen.getByRole("button", { name: /Lancer les services/ });
    expect(bouton.textContent).toBe("Relancer");
    expect(bouton.className).toMatch(/red/);
  });

  it("reste dans le bleu de l'activite quand tout tourne", () => {
    // ADR-026 : cinq familles d'etat, et elles seules.
    render(
      <BoutonServices
        services={etat({ enCours: true })}
        libelleDuProjet="ide-core"
      />,
    );

    expect(screen.getByRole("button").className).toMatch(/blue/);
  });

  it("porte la cause du refus en infobulle", () => {
    // Le 409 dit quoi ecrire dans `agents.json` : le perdre renverrait lire
    // le code.
    render(
      <BoutonServices
        services={etat({ erreur: "ne déclare aucun service : ajoute `services`" })}
        libelleDuProjet="ide-core"
      />,
    );

    expect(screen.getByRole("button").getAttribute("title")).toContain(
      "services",
    );
  });
});
