import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjetsView from "./index";
import { api } from "../../lib/api";
import type { Project, ProjectOverview } from "../../types/api";

vi.mock("../../lib/api", () => ({
  api: {
    projects: { overview: vi.fn(), setCategory: vi.fn() },
  },
}));

const overview = vi.mocked(api.projects.overview);
const setCategory = vi.mocked(api.projects.setCategory);

function vue(id: string, nom: string, extra: Partial<ProjectOverview> = {}): ProjectOverview {
  return {
    id,
    name: nom,
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-09-01T10:00:00Z",
    last_activity: "2026-10-01T10:00:00Z",
    tickets: { todo: 2, in_progress: 1, in_review: 0, blocked: 3, done: 4 },
    run_actif: false,
    icon: false,
    ...extra,
  };
}

function complet(v: ProjectOverview): Project {
  return {
    id: v.id,
    name: v.name,
    path: `/workspace/${v.id}`,
    description: v.description,
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: v.github_remote,
    category: v.category,
  };
}

const DEMINEUR = vue("demineur", "Démineur", {
  category: "Jeux",
  description: "Un démineur en React",
  github_remote: "moi/demineur",
  last_activity: "2026-10-02T10:00:00Z",
});
const SERPENT = vue("serpent", "Serpent", {
  category: "Jeux",
  description: "Le serpent classique",
  last_activity: "2026-10-10T10:00:00Z",
});
const IDE = vue("ide-core", "ide-core", {
  category: "Outils",
  description: "L'IDE lui-même",
  last_activity: null,
});
const TROIS = [DEMINEUR, SERPENT, IDE];

function afficher(
  donnees: ProjectOverview[] = TROIS,
  surSelection: (p: Project) => void = vi.fn(),
  actif: Project | null = null,
) {
  overview.mockResolvedValue(donnees);
  return render(
    <ProjetsView
      projets={donnees.map(complet)}
      activeProject={actif}
      onSelectProject={surSelection}
    />,
  );
}

const cartes = () => screen.getAllByRole("article").map((a) => a.getAttribute("aria-label"));

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe("ProjetsView", () => {
  it("shows one card per project under one heading per category", async () => {
    afficher();

    expect(await screen.findAllByRole("article")).toHaveLength(3);
    const titres = screen.getAllByRole("heading", { level: 2 });
    expect(titres.map((t) => t.textContent)).toEqual(["Jeux", "Outils"]);
  });

  it("keeps only the matching project when searching without case or accents", async () => {
    afficher();
    await screen.findAllByRole("article");

    await userEvent.type(screen.getByRole("searchbox", { name: "Chercher un projet" }), "deminéur");

    expect(cartes()).toEqual(["Démineur"]);
  });

  it("filters by category pill and shows each category's count", async () => {
    afficher();
    await screen.findAllByRole("article");

    const jeux = screen.getByRole("button", { name: /^Jeux\s*2$/ });
    expect(screen.getByRole("button", { name: /^Toutes\s*3$/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Outils\s*1$/ })).toBeInTheDocument();

    await userEvent.click(jeux);

    expect(cartes()).toEqual(["Démineur", "Serpent"]);
    expect(screen.queryByRole("heading", { level: 2 })).not.toBeInTheDocument();
  });

  it("puts the most recently active project first when sorted by activity", async () => {
    afficher();
    await screen.findAllByRole("article");
    expect(cartes()).toEqual(["Démineur", "Serpent", "ide-core"]);

    await userEvent.selectOptions(
      screen.getByRole("combobox", { name: "Trier les projets" }),
      "activite",
    );

    expect(cartes()).toEqual(["Serpent", "Démineur", "ide-core"]);
  });

  it("selects the project on card click but not on repository link click", async () => {
    const surSelection = vi.fn();
    afficher(TROIS, surSelection);
    const carte = await screen.findByRole("article", { name: "Démineur" });

    await userEvent.click(
      within(carte).getByRole("link", { name: "Ouvrir le dépôt de Démineur" }),
    );
    expect(surSelection).not.toHaveBeenCalled();

    await userEvent.click(carte);
    expect(surSelection).toHaveBeenCalledWith(complet(DEMINEUR));
  });

  it("selects the project when Enter is pressed on the focused card", async () => {
    const surSelection = vi.fn();
    afficher(TROIS, surSelection);
    const carte = await screen.findByRole("article", { name: "Serpent" });

    carte.focus();
    await userEvent.keyboard("{Enter}");

    expect(surSelection).toHaveBeenCalledWith(complet(SERPENT));
  });

  it("shows the initial of a project without icon", async () => {
    afficher();
    const carte = await screen.findByRole("article", { name: "Serpent" });

    expect(within(carte).getByTestId("icone-initiale")).toHaveTextContent("S");
  });

  it("shows the project icon when the project has one", async () => {
    afficher([vue("serpent", "Serpent", { icon: true })]);
    const carte = await screen.findByRole("article", { name: "Serpent" });

    expect(within(carte).queryByTestId("icone-initiale")).not.toBeInTheDocument();
    expect(carte.querySelector("img")?.getAttribute("src")).toContain(
      "/api/v1/projects/serpent/icon",
    );
  });

  it("marks the active project and shows the ticket counters and the run dot", async () => {
    const actif = complet(SERPENT);
    afficher([SERPENT, vue("lyra", "Lyra", { run_actif: true })], vi.fn(), actif);
    const carte = await screen.findByRole("article", { name: "Serpent" });

    expect(carte).toHaveAttribute("aria-current", "true");
    expect(carte.className).toContain("border-l-violet-500");
    expect(carte).toHaveTextContent("À faire 2");
    expect(carte).toHaveTextContent("En cours 1");
    expect(carte).toHaveTextContent("Bloqués 3");
    expect(carte).toHaveTextContent("Faits 4");
    expect(within(carte).queryByRole("status")).not.toBeInTheDocument();
    const lyra = screen.getByRole("article", { name: "Lyra" });
    expect(within(lyra).getByRole("status")).toBeInTheDocument();
  });

  it("changes the category from a card menu then reloads the overview", async () => {
    setCategory.mockResolvedValue({} as Awaited<ReturnType<typeof api.projects.setCategory>>);
    afficher();
    const carte = await screen.findByRole("article", { name: "Serpent" });
    expect(overview).toHaveBeenCalledTimes(1);

    await userEvent.click(
      within(carte).getByRole("button", { name: "Changer la catégorie de Serpent" }),
    );
    await userEvent.click(screen.getByRole("menuitem", { name: "Outils" }));

    expect(setCategory).toHaveBeenCalledWith("serpent", "Outils");
    await waitFor(() => expect(overview).toHaveBeenCalledTimes(2));
  });

  it("creates a new category and removes one from the menu without selecting the project", async () => {
    setCategory.mockResolvedValue({} as Awaited<ReturnType<typeof api.projects.setCategory>>);
    const surSelection = vi.fn();
    afficher(TROIS, surSelection);
    const carte = await screen.findByRole("article", { name: "Serpent" });

    await userEvent.click(
      within(carte).getByRole("button", { name: "Changer la catégorie de Serpent" }),
    );
    await userEvent.type(screen.getByRole("textbox", { name: "Nouvelle catégorie" }), "Arcade");
    await userEvent.click(screen.getByRole("button", { name: "Créer" }));
    expect(setCategory).toHaveBeenLastCalledWith("serpent", "Arcade");

    await userEvent.click(
      within(carte).getByRole("button", { name: "Changer la catégorie de Serpent" }),
    );
    await userEvent.click(screen.getByRole("menuitem", { name: "Retirer de la catégorie" }));
    expect(setCategory).toHaveBeenLastCalledWith("serpent", "");
    expect(surSelection).not.toHaveBeenCalled();
  });

  it("shows an error with a retry button, then the projects after retrying", async () => {
    overview.mockRejectedValueOnce(new Error("API 500: boom"));
    afficher();
    expect(await screen.findByText(/API 500/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));

    expect(await screen.findAllByRole("article")).toHaveLength(3);
  });

  it("shows an empty state with a button that clears the search", async () => {
    afficher();
    await screen.findAllByRole("article");
    await userEvent.type(screen.getByRole("searchbox"), "zzz");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Effacer la recherche" }));

    expect(screen.getAllByRole("article")).toHaveLength(3);
  });

  it("restores the search after the view is mounted again", async () => {
    const premier = afficher();
    await screen.findAllByRole("article");
    await userEvent.type(screen.getByRole("searchbox"), "serp");

    premier.unmount();
    afficher();

    await waitFor(() => expect(screen.getByRole("searchbox")).toHaveValue("serp"));
    expect(cartes()).toEqual(["Serpent"]);
  });
});
