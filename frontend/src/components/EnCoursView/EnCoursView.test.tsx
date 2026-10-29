import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import EnCoursView from "./index";
import { api } from "../../lib/api";
import type { UseAppsEnCoursResult } from "../../hooks/useAppsEnCours";
import { boutonsPleins } from "../../test/boutons";
import type { AppEnCours } from "../../types/api";

function app(over: Partial<AppEnCours>): AppEnCours {
  return {
    project_id: "alpha",
    project_name: "Alpha",
    nom: "api",
    origine: "tessera",
    pid: 100,
    ports: [8001],
    demarre_a: "2026-10-13T10:00:00Z",
    memoire_mo: 100,
    ...over,
  };
}

function rendre(
  apps: AppEnCours[] | null,
  over: Partial<UseAppsEnCoursResult> = {},
) {
  const arreter = vi.fn().mockResolvedValue(undefined);
  render(
    <EnCoursView
      vueInitiale="liste"
      appsEnCours={{
        apps,
        lueA: Date.parse("2026-10-13T12:00:00Z"),
        erreur: null,
        arreter,
        rafraichir: vi.fn(),
        arreterProjet: vi.fn().mockResolvedValue(undefined),
        lancer: vi.fn().mockResolvedValue(undefined),
        enArret: () => false,
        enLancement: () => false,
        ...over,
      }}
    />,
  );
  return arreter;
}

const TROIS = [
  app({ pid: 1, nom: "front", ports: [5301], memoire_mo: 120.5 }),
  app({
    pid: 2,
    project_id: "beta",
    project_name: "Beta",
    nom: "serveur",
    origine: "externe",
    ports: [8002, 8003],
    memoire_mo: 480,
  }),
  app({ pid: 3, project_id: "gamma", project_name: "Gamma", nom: "docs", memoire_mo: 30 }),
];

beforeEach(() => {
  vi.spyOn(api.projects, "overview").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("EnCoursView", () => {
  it("lists each app with its project, port links and memory, heaviest first", () => {
    rendre(TROIS);

    const lignes = screen.getAllByRole("listitem");
    expect(lignes.map((l) => within(l).getByText(/^[a-z]+$/).textContent)).toEqual([
      "serveur",
      "front",
      "docs",
    ]);
    expect(screen.getByRole("heading", { name: "Beta" })).toBeInTheDocument();
    expect(screen.getByText("480,0 Mo")).toBeInTheDocument();
    expect(screen.getByText("Lancé à la main")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "localhost:8003" })).toHaveAttribute(
      "href",
      "http://localhost:8003",
    );
  });

  it("shows a dash instead of a link for an app without a port", () => {
    rendre([app({ pid: 5, nom: "worker", origine: "externe", ports: [] })]);
    const ligne = screen.getByText("worker").closest("li") as HTMLElement;

    expect(within(ligne).getByText("—")).toBeInTheDocument();
    expect(within(ligne).queryByRole("link")).not.toBeInTheDocument();
  });

  it("shows the sum of the apps as total memory", () => {
    rendre(TROIS);
    expect(screen.getByText(/Mémoire totale : 630,5 Mo/)).toBeInTheDocument();
  });

  it("asks for confirmation before stopping an external app", async () => {
    const arreter = rendre(TROIS);
    const ligne = screen.getByText("serveur").closest("li") as HTMLElement;

    await userEvent.click(within(ligne).getByRole("button", { name: /Arrêter/ }));
    expect(arreter).not.toHaveBeenCalled();
    expect(screen.getByText("Arrêter le processus 2 ?")).toBeInTheDocument();

    await userEvent.click(within(ligne).getByRole("button", { name: "Confirmer" }));
    expect(arreter).toHaveBeenCalledWith(2);
  });

  it("cancels the confirmation without stopping anything", async () => {
    const arreter = rendre(TROIS);
    const ligne = screen.getByText("serveur").closest("li") as HTMLElement;

    await userEvent.click(within(ligne).getByRole("button", { name: /Arrêter/ }));
    await userEvent.click(within(ligne).getByRole("button", { name: "Annuler" }));

    expect(arreter).not.toHaveBeenCalled();
    expect(within(ligne).getByRole("button", { name: /Arrêter/ })).toBeInTheDocument();
  });

  it("stops a Tessera app at once, without confirmation", async () => {
    const arreter = rendre(TROIS);
    const ligne = screen.getByText("front").closest("li") as HTMLElement;

    await userEvent.click(within(ligne).getByRole("button", { name: /Arrêter/ }));

    expect(screen.queryByText(/Arrêter le processus/)).not.toBeInTheDocument();
    expect(arreter).toHaveBeenCalledWith(1);
  });

  it("shows the empty state when nothing runs", () => {
    rendre([]);
    expect(screen.getByText("Aucune app de projet ne tourne")).toBeInTheDocument();
  });

  it("shows a loading state before the first read", () => {
    rendre(null);
    expect(screen.getByText("Chargement…")).toBeInTheDocument();
  });

  it("shows the error when the first read fails", () => {
    rendre(null, { erreur: "API 500: boom" });
    expect(screen.getByRole("alert")).toHaveTextContent("API 500: boom");
  });

  it("keeps the list visible when a later read fails", () => {
    rendre(TROIS, { erreur: "Arrêt impossible" });
    expect(screen.getByRole("alert")).toHaveTextContent("Arrêt impossible");
    expect(screen.getByText("front")).toBeInTheDocument();
  });
});

describe("EnCoursView — composants communs (ticket-442)", () => {
  it("draws Arrêter as a Button in the arret variant", () => {
    rendre(TROIS);
    const ligne = screen.getByText("front").closest("li") as HTMLElement;
    const bouton = within(ligne).getByRole("button", { name: /Arrêter/ });

    expect(bouton.className).toMatch(/border-red-/);
    expect(bouton.className).not.toMatch(/(^|\s)bg-red-/);
  });

  it("draws the origin of an app with the shared StatusPill", () => {
    rendre(TROIS);
    expect(screen.getByText("Lancé à la main")).toHaveAttribute("data-etat", "attention");
    expect(screen.getAllByText("Tessera")[0]).toHaveAttribute("data-etat", "en-cours");
  });

  it("has at most one plein button", () => {
    rendre(TROIS);
    expect(boutonsPleins().length).toBeLessThanOrEqual(1);
  });
});
