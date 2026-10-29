import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EnCoursView from "./index";
import { api } from "../../lib/api";
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

function rendre(apps: AppEnCours[] | null) {
  const etat: UseAppsEnCoursResult = {
    apps,
    lueA: Date.parse("2026-10-13T12:00:00Z"),
    erreur: null,
    arreter: vi.fn().mockResolvedValue(undefined),
    rafraichir: vi.fn(),
    arreterProjet: vi.fn().mockResolvedValue(undefined),
    lancer: vi.fn().mockResolvedValue(undefined),
    enArret: () => false,
    enLancement: () => false,
  };
  return render(<EnCoursView appsEnCours={etat} />);
}

const SPRITES_DU_BUREAU = ["fenetre", "plante", "porte", "etagere"];
const SPRITES_DE_PERSONNAGE = ["personnage", "agent-debout"];

function sprites(racine: HTMLElement): string[] {
  return [...racine.querySelectorAll("[data-sprite]")].map(
    (el) => el.getAttribute("data-sprite") ?? "",
  );
}

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.projects, "overview").mockResolvedValue([]);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("SallesDesServeurs", () => {
  it("draws one room per app, and none when the list is empty", () => {
    const { unmount } = rendre([app({ pid: 1 }), app({ pid: 2, project_id: "beta", project_name: "Beta" })]);
    expect(screen.getAllByRole("complementary")).toHaveLength(2);
    unmount();

    rendre([]);
    expect(screen.queryAllByRole("complementary")).toHaveLength(0);
    expect(screen.getByText("Aucune app de projet ne tourne")).toBeInTheDocument();
  });

  it("writes the project, ports, memory and start time read from the app", () => {
    rendre([app({ project_name: "Alpha", ports: [8001, 8002], memoire_mo: 120.5 })]);

    const salle = screen.getByRole("complementary", { name: /Alpha/ });
    expect(within(salle).getByRole("heading", { name: /Alpha/ })).toBeInTheDocument();
    expect(within(salle).getByText("Ports :8001 :8002")).toBeInTheDocument();
    expect(within(salle).getByText("120,5 Mo")).toBeInTheDocument();
    expect(within(salle).getByText(/Démarrée à \d{2}:\d{2}/)).toBeInTheDocument();
  });

  it("writes a dash for the start time and ports the app does not give", () => {
    rendre([app({ demarre_a: null, ports: [] })]);

    expect(screen.getByText("Démarrée à —")).toBeInTheDocument();
    expect(screen.getByText("Ports —")).toBeInTheDocument();
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
    const [marche, arret] = voyants.map((v) => v.querySelector("rect")?.getAttribute("class"));
    expect(marche).toBeTruthy();
    expect(arret).toBeTruthy();
    expect(marche).not.toEqual(arret);
    expect(screen.getByText("worker — à l'arrêt")).toBeInTheDocument();
  });

  it("draws a single running rack for an app whose project declares no service", () => {
    rendre([app({ nom: "serveur", origine: "externe" })]);

    expect(document.querySelectorAll("[data-sprite='baie-haute']")).toHaveLength(1);
    expect(document.querySelector("[data-voyant]")).toHaveAttribute("data-voyant", "en-cours");
    expect(screen.getByText("serveur — en cours")).toBeInTheDocument();
  });

  it("furnishes the room with the technical sprites and none from the offices", () => {
    const { container } = rendre([app({})]);
    const dessines = sprites(container);

    for (const sprite of ["climatiseur", "chemin-de-cables", "extincteur", "porte-coupe-feu", "baie-haute"]) {
      expect(dessines, sprite).toContain(sprite);
    }
    for (const sprite of SPRITES_DU_BUREAU) {
      expect(dessines, sprite).not.toContain(sprite);
    }
  });

  it("draws no character in a room", () => {
    const { container } = rendre([app({}), app({ pid: 2 })]);

    for (const sprite of SPRITES_DE_PERSONNAGE) {
      expect(sprites(container), sprite).not.toContain(sprite);
    }
  });

  it("keeps the list view in the switcher", async () => {
    rendre([app({ nom: "api" })]);

    await userEvent.click(screen.getByRole("button", { name: "Liste" }));

    expect(screen.queryAllByRole("complementary")).toHaveLength(0);
    expect(screen.getByRole("button", { name: "Arrêter api" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salles" }));
    expect(screen.getAllByRole("complementary")).toHaveLength(1);
  });
});
