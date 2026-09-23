import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PanneauServices from "./PanneauServices";
import type { UseServicesResult } from "../../hooks/useServices";
import type { ServiceActif } from "../../types/api";

function service(over: Partial<ServiceActif> = {}): ServiceActif {
  return {
    nom: "dev",
    project_id: "fluentdb",
    pid: 4242,
    demarre_a: new Date().toISOString(),
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

function etat(over: Partial<UseServicesResult> = {}): UseServicesResult {
  return {
    services: [service()],
    enCours: true,
    enEchec: false,
    declare: true,
    erreur: null,
    demarrer: vi.fn(),
    arreter: vi.fn(),
    rafraichir: vi.fn(),
    ...over,
  };
}

function rendre(
  over: Partial<UseServicesResult> = {},
  sortie: string[] = [],
  chemin: string | null = "C:/p/fluentdb",
) {
  return render(
    <PanneauServices
      services={etat(over)}
      sortieDe={() => sortie}
      projectId="fluentdb"
      cheminDuProjet={chemin}
    />,
  );
}

describe("PanneauServices", () => {
  it("liste les services declares avec leur etat", () => {
    rendre({
      services: [
        service(),
        service({ nom: "api", en_cours: false, code_de_sortie: null }),
      ],
    });

    expect(screen.getByText("dev")).toBeInTheDocument();
    expect(screen.getByText("en cours")).toBeInTheDocument();
    expect(screen.getByText("à l'arrêt")).toBeInTheDocument();
  });

  it("explique quoi ecrire quand rien n'est declare, au lieu de disparaitre", () => {
    // Le reproche du premier usage : masquer la fonctionnalite repondait au
    // symptome, pas au besoin — on veut lancer son projet.
    rendre({ declare: false, services: [] });

    expect(screen.getByText(/ne déclare aucun service/)).toBeInTheDocument();
    expect(screen.getByText(/"nom": "dev"/)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /Ouvrir agents.json/ }),
    ).toBeInTheDocument();
  });

  it("previent que la commande n'est pas passee a un shell", () => {
    // Sinon le premier reflexe est d'ecrire « npm i && npm run dev ».
    rendre({ declare: false, services: [] });

    expect(screen.getByText(/sans shell/)).toBeInTheDocument();
  });

  it("rend l'adresse cliquable sans qu'on ouvre quoi que ce soit", () => {
    rendre({}, ["  ➜  Local:   http://localhost:5175/"]);

    expect(
      screen.getByRole("link", { name: /localhost:5175/ }).getAttribute("href"),
    ).toBe("http://localhost:5175/");
  });

  it("n'affiche aucune adresse pour un service arrete", () => {
    // Elle menerait vers un serveur qui n'ecoute plus.
    rendre(
      { services: [service({ en_cours: false, code_de_sortie: 1 })] },
      ["Local: http://localhost:5175/"],
    );

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  it("montre les dernieres lignes sans changer de vue", async () => {
    rendre({}, ["compilation", "pret en 300ms"]);

    await userEvent.click(screen.getByRole("button", { name: /dev/ }));

    expect(screen.getByLabelText("Sortie de dev").textContent).toContain(
      "pret en 300ms",
    );
  });

  it("affiche l'erreur en toutes lettres, pas seulement en infobulle", () => {
    rendre({ erreur: "`cwd` sort du périmètre du projet : '../voisin'" });

    expect(screen.getByText(/sort du périmètre/)).toBeInTheDocument();
  });

  it("se passe du lien VSCode quand le projet n'a pas de chemin", () => {
    // Un projet sans chemin ne doit pas couter le panneau entier.
    rendre({ declare: false, services: [] }, [], null);

    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText(/ne déclare aucun service/)).toBeInTheDocument();
  });
});
