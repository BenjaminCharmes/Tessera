import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EnCoursView from "./index";
import { api } from "../../lib/api";
import { lireActivite } from "../../lib/apiActivite";
import { _viderCacheResource } from "../../hooks/useResource";
import type { UseAppsEnCoursResult } from "../../hooks/useAppsEnCours";
import type { AppEnCours, ServiceActif } from "../../types/api";

function app(over: Partial<AppEnCours>): AppEnCours {
  return {
    project_id: "alpha",
    project_name: "Alpha",
    nom: "api",
    origine: "tessera",
    pid: 100,
    ports: [8001],
    demarre_a: "2026-10-13T10:00:00Z",
    memoire_mo: 120.5,
    ...over,
  };
}

function service(over: Partial<ServiceActif>): ServiceActif {
  return {
    nom: "api",
    project_id: "alpha",
    pid: 100,
    demarre_a: "2026-10-13T10:00:00Z",
    en_cours: true,
    code_de_sortie: null,
    ...over,
  };
}

function rendre(apps: AppEnCours[] | null, arreterProjet = vi.fn().mockResolvedValue(undefined)) {
  const etat: UseAppsEnCoursResult = {
    apps,
    lueA: Date.parse("2026-10-13T12:00:00Z"),
    erreur: null,
    arreter: vi.fn().mockResolvedValue(undefined),
    rafraichir: vi.fn(),
    arreterProjet,
    lancer: vi.fn().mockResolvedValue(undefined),
    enArret: () => false,
    enLancement: () => false,
  };
  return render(<EnCoursView appsEnCours={etat} />);
}

const SPRITES_DU_BUREAU = ["fenetre", "plante", "porte", "etagere"];
const SPRITES_DE_PERSONNAGE = ["personnage", "agent-debout"];

function sprites(racine: HTMLElement): string[] {
  return [...racine.querySelectorAll("[data-sprite]")].map((el) => el.getAttribute("data-sprite") ?? "");
}

function salles(): HTMLElement[] {
  return screen.queryAllByRole("article");
}

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.projects, "overview").mockResolvedValue([]);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.mocked(lireActivite).mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

vi.mock("../../lib/apiActivite", () => ({ lireActivite: vi.fn() }));

describe("server rooms — one per project (ticket-710)", () => {
  it("draws one room for two apps of a project, two rooms for two projects, none when empty", () => {
    const { unmount } = rendre([app({ pid: 1, nom: "api" }), app({ pid: 2, nom: "web" })]);
    expect(salles()).toHaveLength(1);
    expect(document.querySelectorAll("[data-sprite='baie-haute']")).toHaveLength(2);
    unmount();

    const autre = rendre([app({ pid: 1 }), app({ pid: 2, project_id: "beta", project_name: "Beta" })]);
    expect(salles()).toHaveLength(2);
    autre.unmount();

    rendre([]);
    expect(salles()).toHaveLength(0);
    expect(screen.getByText("Aucune app de projet ne tourne")).toBeInTheDocument();
  });

  it("writes the project name, the service count and the summed memory on the room's plate", () => {
    rendre([app({ pid: 1, nom: "api", memoire_mo: 100 }), app({ pid: 2, nom: "web", memoire_mo: 20.5 })]);

    const salle = screen.getByRole("article", { name: /Alpha/ });
    expect(within(salle).getByRole("heading", { name: "Alpha" })).toBeInTheDocument();
    expect(within(salle).getByText("2 services · 120,5 Mo")).toBeInTheDocument();
  });

  it("links each port of the project from the plate, named after its service", () => {
    rendre([app({ pid: 1, nom: "backend", ports: [8026] }), app({ pid: 2, nom: "frontend", ports: [5196] })]);

    expect(screen.getByRole("link", { name: /Ouvrir backend :8026/ })).toHaveAttribute("href", "http://localhost:8026");
    expect(screen.getByRole("link", { name: /Ouvrir frontend :5196/ })).toHaveAttribute("href", "http://localhost:5196");
  });

  it("shows a rack's pid, ports and memory in a tooltip on focus", async () => {
    rendre([app({ pid: 4242, ports: [8001], memoire_mo: 90.5 })]);

    fireEvent.focus(screen.getByRole("group", { name: "api : en cours" }));
    const fiche = await screen.findByRole("tooltip");
    expect(within(fiche).getByText("4242")).toBeInTheDocument();
    expect(within(fiche).getByText(":8001")).toBeInTheDocument();
    expect(within(fiche).getByText("90,5 Mo")).toBeInTheDocument();
  });

  it("lays the rooms out in two columns from 1280 px, one below", () => {
    rendre([app({})]);

    const grille = document.querySelector("[data-vue='salles']");
    expect(grille).toHaveClass("grid-cols-1");
    expect(grille).toHaveClass("xl:grid-cols-2");
  });

  it("draws one rack per service, with a lamp that tells a stopped service from a running one", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ nom: "api", en_cours: true }),
      service({ nom: "worker", en_cours: false, pid: 7, arrete_a_la_main: true }),
    ]);
    rendre([app({})]);

    await waitFor(() => expect(document.querySelectorAll("[data-sprite='baie-haute']")).toHaveLength(2));
    const voyants = [...document.querySelectorAll("[data-voyant]")];
    expect(voyants.map((v) => v.getAttribute("data-voyant"))).toEqual(["en-cours", "arrete"]);
  });

  it("furnishes the room with the technical sprites, a tiled floor, and none from the offices", () => {
    const { container } = rendre([app({})]);
    const dessines = sprites(container);

    for (const sprite of ["climatiseur", "chemin-de-cables", "extincteur", "porte-coupe-feu", "baie-haute", "bouche-vmc", "dalle-pleine", "dalle-perforee"]) {
      expect(dessines, sprite).toContain(sprite);
    }
    for (const sprite of SPRITES_DU_BUREAU) {
      expect(dessines, sprite).not.toContain(sprite);
    }
    for (const sprite of SPRITES_DE_PERSONNAGE) {
      expect(dessines, sprite).not.toContain(sprite);
    }
  });

  it("spins the vent only while a service runs, faster with the project's memory", async () => {
    const { unmount } = rendre([app({ memoire_mo: 120 })]);
    expect(document.querySelector("[data-sprite='bouche-vmc']")).toHaveAttribute("data-regime", "lent");
    unmount();

    rendre([app({ memoire_mo: 900 })]);
    expect(document.querySelector("[data-sprite='bouche-vmc']")).toHaveAttribute("data-regime", "rapide");
  });

  it("stops the vent when no service of the project runs", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ nom: "api", en_cours: false, pid: 7, arrete_a_la_main: true }),
    ]);
    rendre([app({ nom: "api" })]);

    await waitFor(() =>
      expect(document.querySelector("[data-sprite='bouche-vmc']")).toHaveAttribute("data-regime", "arret"),
    );
  });

  it("stops the whole project from the room's plate", async () => {
    const arreterProjet = vi.fn().mockResolvedValue(undefined);
    const apps = [app({ pid: 1, nom: "api" }), app({ pid: 2, nom: "web" })];
    rendre(apps, arreterProjet);

    await userEvent.click(screen.getByRole("button", { name: "Arrêter le projet Alpha" }));
    expect(arreterProjet).toHaveBeenCalledWith("alpha", expect.arrayContaining(apps));
  });

  it("keeps the list view in the switcher", async () => {
    rendre([app({ nom: "api" })]);

    await userEvent.click(screen.getByRole("button", { name: "Liste" }));
    expect(salles()).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Arrêter api" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salles" }));
    expect(salles()).toHaveLength(1);
  });
});

describe("wall screens and journal (ticket-711)", () => {
  const SORTIE = ["boot", "GET / 200", "WARN slow query", "GET /a 200", "Error: connect ECONNREFUSED", "retry"];

  async function rendreAvecSortie(over: Partial<ServiceActif> = {}) {
    vi.spyOn(api.services, "list").mockResolvedValue([service({ sortie: SORTIE, ...over })]);
    rendre([app({})]);
    return screen.findByRole("button", { name: /api/, expanded: false });
  }

  it("shows the last five lines of a service's output, an error line in red", async () => {
    const ecran = await rendreAvecSortie();

    expect(within(ecran).queryByText("boot")).toBeNull();
    expect(within(ecran).getByText("retry")).toBeInTheDocument();
    expect(within(ecran).getByText("Error: connect ECONNREFUSED")).toHaveClass("text-red-300");
    expect(within(ecran).getByText("WARN slow query")).toHaveClass("text-amber-300");
  });

  it("opens the journal under the room on a click, and closes it on a second click", async () => {
    const ecran = await rendreAvecSortie();

    fireEvent.click(ecran);
    expect(screen.getByRole("region", { name: "Journal de Alpha · api" })).toBeInTheDocument();
    expect(ecran).toHaveAttribute("aria-expanded", "true");
    fireEvent.click(ecran);
    expect(screen.queryByRole("region", { name: /Journal de/ })).toBeNull();
  });

  it("closes the journal with its close button", async () => {
    fireEvent.click(await rendreAvecSortie());

    fireEvent.click(screen.getByRole("button", { name: "Fermer le journal" }));
    expect(screen.queryByRole("region", { name: /Journal de/ })).toBeNull();
  });

  it("closes the journal with Escape when the focus is inside it", async () => {
    fireEvent.click(await rendreAvecSortie());

    fireEvent.keyDown(screen.getByRole("searchbox", { name: "Chercher dans le journal" }), { key: "Escape" });
    expect(screen.queryByRole("region", { name: /Journal de/ })).toBeNull();
  });

  it("filters the journal to errors, and by the searched text", async () => {
    fireEvent.click(await rendreAvecSortie());
    const journal = screen.getByRole("region", { name: /Journal de/ });

    fireEvent.click(within(journal).getByRole("button", { name: /Erreurs · 1/ }));
    expect(within(journal).getByText("Error: connect ECONNREFUSED")).toBeInTheDocument();
    expect(within(journal).queryByText("retry")).toBeNull();

    fireEvent.click(within(journal).getByRole("button", { name: /Tout · 6/ }));
    fireEvent.change(within(journal).getByRole("searchbox", { name: "Chercher dans le journal" }), {
      target: { value: "slow" },
    });
    expect(within(journal).getByText("WARN slow query")).toBeInTheDocument();
    expect(within(journal).queryByText("boot")).toBeNull();
  });

  it("marks a service that died on its own as fallen, but not one stopped by hand", async () => {
    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ en_cours: false, code_de_sortie: 1, arrete_a_la_main: false }),
    ]);
    const { unmount } = rendre([app({})]);
    await waitFor(() => expect(screen.getByRole("article")).toHaveAttribute("data-tombe", "true"));
    expect(document.querySelector("[data-voyant]")).toHaveAttribute("data-voyant", "echoue");
    unmount();
    _viderCacheResource();

    vi.spyOn(api.services, "list").mockResolvedValue([
      service({ en_cours: false, code_de_sortie: 1, arrete_a_la_main: true }),
    ]);
    rendre([app({})]);
    await waitFor(() => expect(document.querySelector("[data-voyant]")).toHaveAttribute("data-voyant", "arrete"));
    expect(screen.getByRole("article")).toHaveAttribute("data-tombe", "false");
  });

  it("draws no wall screen for an app launched by hand, whose output Tessera does not have", () => {
    rendre([app({ nom: "serveur", origine: "externe" })]);

    expect(document.querySelector("[data-ecran-mural]")).toBeNull();
    expect(document.querySelectorAll("[data-sprite='baie-haute']")).toHaveLength(1);
  });
});
