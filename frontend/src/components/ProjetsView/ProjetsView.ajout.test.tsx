import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjetsView from "./index";
import { api } from "../../lib/api";
import type { Project, ProjectOverview } from "../../types/api";

vi.mock("../../lib/api", () => ({
  api: {
    projects: { overview: vi.fn(), setCategory: vi.fn() },
    services: { start: vi.fn(), stop: vi.fn() },
  },
}));

// Les modales ont leurs propres tests : ici on ne vérifie que le câblage.
vi.mock("../Sidebar/CreateProjectModal", () => ({
  default: ({ onCreated }: { onCreated: (p: Project) => void }) => (
    <div role="dialog" aria-label="Création">
      <button type="button" onClick={() => onCreated(NOUVEAU)}>
        Valider la création
      </button>
    </div>
  ),
}));
vi.mock("../Sidebar/ImportProjectModal", () => ({
  default: ({ onProjectCreated }: { onProjectCreated: (p: Project) => void }) => (
    <div role="dialog" aria-label="Import">
      <button type="button" onClick={() => onProjectCreated(NOUVEAU)}>
        Valider l&apos;import
      </button>
    </div>
  ),
}));

const overview = vi.mocked(api.projects.overview);

function vue(id: string, nom: string): ProjectOverview {
  return {
    id,
    name: nom,
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-09-01T10:00:00Z",
    last_activity: null,
    tickets: { todo: 0, in_progress: 0, in_review: 0, blocked: 0, done: 0 },
    run_actif: false,
    icon: false,
    services_declares: false,
    services_en_cours: false,
    online_declared: false,
  };
}

const NOUVEAU: Project = {
  id: "nouveau",
  name: "Nouveau",
  path: "/workspace/nouveau",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
  category: null,
};

const VUES = [vue("serpent", "Serpent"), vue("demineur", "Démineur")];

function afficher(extra: { enAttente?: ReadonlySet<string> } = {}) {
  overview.mockResolvedValue(VUES);
  const onSelectProject = vi.fn();
  const onProjectCreated = vi.fn();
  render(
    <ProjetsView
      projets={[]}
      activeProject={null}
      onSelectProject={onSelectProject}
      onProjectCreated={onProjectCreated}
      {...extra}
    />,
  );
  return { onSelectProject, onProjectCreated };
}

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

describe("ProjetsView — adding a project (ticket-586)", () => {
  it("opens the creation modal and makes the created project active", async () => {
    const { onSelectProject, onProjectCreated } = afficher();
    await screen.findAllByRole("article");

    await userEvent.click(screen.getByRole("button", { name: "Créer un projet" }));
    expect(screen.getByRole("dialog", { name: "Création" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Valider la création" }));

    expect(onProjectCreated).toHaveBeenCalledWith(NOUVEAU);
    expect(onSelectProject).toHaveBeenCalledWith(NOUVEAU);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens the import modal and makes the imported project active", async () => {
    const { onSelectProject, onProjectCreated } = afficher();
    await screen.findAllByRole("article");

    await userEvent.click(screen.getByRole("button", { name: "Importer un projet" }));
    expect(screen.getByRole("dialog", { name: "Import" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Valider l'import" }));

    expect(onProjectCreated).toHaveBeenCalledWith(NOUVEAU);
    expect(onSelectProject).toHaveBeenCalledWith(NOUVEAU);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("opens no modal until a button is clicked", async () => {
    afficher();
    await screen.findAllByRole("article");

    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("ProjetsView — a run waiting for an answer (ticket-586)", () => {
  it("marks only the card of the project that is waiting", async () => {
    afficher({ enAttente: new Set(["serpent"]) });
    await screen.findAllByRole("article");

    const serpent = screen.getByRole("article", { name: "Serpent" });
    const demineur = screen.getByRole("article", { name: "Démineur" });
    expect(within(serpent).getByLabelText("Un agent attend une réponse")).toBeInTheDocument();
    expect(within(demineur).queryByLabelText("Un agent attend une réponse")).toBeNull();
  });
});
