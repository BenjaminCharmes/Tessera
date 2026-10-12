import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../../lib/api";
import ProjectNav from "./ProjectNav";
import type { Project } from "../../types/api";

const CLE = "tessera.categories-repliees";

function projet(id: string, category: string | null = null): Project {
  return {
    id,
    name: id,
    path: `/w/${id}`,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
    category,
  };
}

const PROJETS = [
  projet("demineur", "jeux"),
  projet("serpent", "jeux"),
  projet("cookie_clicker", "jeux"),
  projet("ide-core", "outils"),
];

function monter(actif: Project | null = null) {
  return render(<ProjectNav activeProject={actif} onSelectProject={vi.fn()} />);
}

beforeEach(() => {
  vi.restoreAllMocks();
  window.localStorage.clear();
  vi.spyOn(api.projects, "list").mockResolvedValue(PROJETS);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("ProjectNav — catégories repliables (ticket-400)", () => {
  it("masque les projets d'une catégorie au clic sur son titre, et les rend au second", async () => {
    monter();
    const titre = await screen.findByRole("button", { name: /jeux/i });
    expect(titre).toHaveAttribute("aria-expanded", "true");

    await userEvent.click(titre);
    expect(screen.queryByText("serpent")).toBeNull();
    expect(screen.getByText("ide-core")).toBeInTheDocument();
    expect(titre).toHaveAttribute("aria-expanded", "false");

    await userEvent.click(titre);
    expect(screen.getByText("serpent")).toBeInTheDocument();
    expect(titre).toHaveAttribute("aria-expanded", "true");
  });

  it("affiche le nombre de projets d'une catégorie repliée, avec une info-bulle qui les nomme", async () => {
    monter();
    const titre = await screen.findByRole("button", { name: /jeux/i });
    expect(screen.queryByText("3")).toBeNull();

    await userEvent.click(titre);

    expect(screen.getByText("3")).toBeInTheDocument();
    expect(titre).toHaveAttribute(
      "title",
      "3 projets : demineur, serpent, cookie_clicker",
    );
  });

  it("accorde l'info-bulle au singulier", async () => {
    monter();
    const titre = await screen.findByRole("button", { name: /outils/i });

    await userEvent.click(titre);

    expect(titre).toHaveAttribute("title", "1 projet : ide-core");
  });

  it("mémorise le pli dans localStorage", async () => {
    monter();
    await userEvent.click(await screen.findByRole("button", { name: /jeux/i }));

    expect(JSON.parse(window.localStorage.getItem(CLE) ?? "[]")).toEqual(["jeux"]);
  });

  it("relit l'état replié depuis localStorage au montage", async () => {
    window.localStorage.setItem(CLE, JSON.stringify(["jeux"]));

    monter();

    const titre = await screen.findByRole("button", { name: /jeux/i });
    expect(titre).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("serpent")).toBeNull();
    expect(screen.getByText("ide-core")).toBeInTheDocument();
  });

  it("laisse tout déplié, sans erreur, quand localStorage lève", async () => {
    vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
      throw new Error("bloque");
    });
    vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
      throw new Error("bloque");
    });

    monter();

    await screen.findByText("serpent");
    expect(screen.getByText("ide-core")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /jeux/i })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("ignore un contenu mémorisé illisible", async () => {
    window.localStorage.setItem(CLE, "{pas du json");

    monter();

    expect(await screen.findByText("serpent")).toBeInTheDocument();
  });

  it("garde visible le projet actif d'une catégorie repliée", async () => {
    window.localStorage.setItem(CLE, JSON.stringify(["jeux"]));

    monter(PROJETS[1]);

    await screen.findByRole("button", { name: /jeux/i });
    expect(screen.getByText("serpent")).toBeInTheDocument();
    expect(screen.queryByText("demineur")).toBeNull();
    expect(screen.queryByText("cookie_clicker")).toBeNull();
    // Le badge compte tous les projets de la catégorie, pas seulement ceux affichés.
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("ne replie pas seule la catégorie du projet actif", async () => {
    monter(PROJETS[0]);

    const titre = await screen.findByRole("button", { name: /jeux/i });
    expect(titre).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("cookie_clicker")).toBeInTheDocument();
  });
});
