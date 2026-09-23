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

  it("affiche la sortie gardee par le backend, sans avoir ecoute le canal", async () => {
    // Le cas vecu : un service lance avant l'ouverture de l'IDE affichait
    // « n'a encore rien ecrit », alors qu'il tournait depuis dix minutes.
    render(
      <PanneauServices
        services={etat({
          services: [service({ sortie: ["Local: http://localhost:5175/"] })],
        })}
        sortieDe={() => []}
        projectId="fluentdb"
        cheminDuProjet={null}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /dev/ }));

    expect(screen.getByLabelText("Sortie de dev").textContent).toContain(
      "localhost:5175",
    );
  });

  it("retrouve l'adresse depuis la sortie gardee", () => {
    // C'est elle qui portait l'URL, et elle etait perdue au rechargement.
    render(
      <PanneauServices
        services={etat({
          services: [service({ sortie: ["  ➜  Local:   http://localhost:5175/"] })],
        })}
        sortieDe={() => []}
        projectId="fluentdb"
        cheminDuProjet={null}
      />,
    );

    expect(
      screen.getByRole("link", { name: /localhost:5175/ }).getAttribute("href"),
    ).toBe("http://localhost:5175/");
  });

  it("prefere le direct quand il est plus complet", () => {
    // Le canal reste la source vivante : la memoire du backend ne sert qu'au
    // rattrapage.
    render(
      <PanneauServices
        services={etat({ services: [service({ sortie: ["vieille ligne"] })] })}
        sortieDe={() => ["ligne une", "ligne deux", "ligne trois"]}
        projectId="fluentdb"
        cheminDuProjet={null}
      />,
    );

    void userEvent.click(screen.getByRole("button", { name: /dev/ }));
    return vi.waitFor(() =>
      expect(screen.getByLabelText("Sortie de dev").textContent).toContain(
        "ligne trois",
      ),
    );
  });
});

describe("PanneauServices — plusieurs services (ticket-148)", () => {
  it("garde deux sorties ouvertes en meme temps", async () => {
    // Un projet qui lance un backend **et** un frontend veut voir les deux :
    // l'accordeon fermait l'une en ouvrant l'autre.
    render(
      <PanneauServices
        services={etat({
          services: [
            service({ nom: "backend", sortie: ["api prete"] }),
            service({ nom: "frontend", sortie: ["vite pret"] }),
          ],
        })}
        sortieDe={() => []}
        projectId="mon-projet"
        cheminDuProjet={null}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /backend/ }));
    await userEvent.click(screen.getByRole("button", { name: /frontend/ }));

    expect(screen.getByLabelText("Sortie de backend")).toBeInTheDocument();
    expect(screen.getByLabelText("Sortie de frontend")).toBeInTheDocument();
  });

  it("referme celle qu'on rouvre, sans toucher a l'autre", async () => {
    render(
      <PanneauServices
        services={etat({
          services: [
            service({ nom: "backend", sortie: ["api prete"] }),
            service({ nom: "frontend", sortie: ["vite pret"] }),
          ],
        })}
        sortieDe={() => []}
        projectId="mon-projet"
        cheminDuProjet={null}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /backend/ }));
    await userEvent.click(screen.getByRole("button", { name: /frontend/ }));
    await userEvent.click(screen.getByRole("button", { name: /backend/ }));

    expect(screen.queryByLabelText("Sortie de backend")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Sortie de frontend")).toBeInTheDocument();
  });
});

describe("PanneauServices — le projet qui fait tourner l'IDE (ticket-152)", () => {
  it("dit ce qu'il est, au lieu de proposer un lancement", () => {
    // Cliquer « Lancer » sur ide-core demarrait un second backend sur un port
    // deja pris. Le cas utile n'existe pas : il faut que l'IDE tourne pour
    // qu'on voie l'ecran.
    render(
      <PanneauServices
        services={etat()}
        sortieDe={() => []}
        projectId="ide-core"
        cheminDuProjet="C:/p/tessera"
        faitTournerLIde
      />,
    );

    expect(screen.getByText(/fait tourner l'IDE/)).toBeInTheDocument();
    expect(screen.queryByText(/ne déclare aucun service/)).not.toBeInTheDocument();
  });

  it("ne propose ni logs ni arret pour ces serveurs", () => {
    // Ils n'ont pas ete lances par l'IDE : leur sortie ne passe pas par un
    // tube qu'il controle, et les tuer serait une decision d'un autre ordre.
    render(
      <PanneauServices
        services={etat()}
        sortieDe={() => ["des lignes"]}
        projectId="ide-core"
        cheminDuProjet={null}
        faitTournerLIde
      />,
    );

    expect(screen.queryByLabelText(/Sortie de/)).not.toBeInTheDocument();
    expect(screen.getByText(/passe par le terminal/)).toBeInTheDocument();
  });
});
