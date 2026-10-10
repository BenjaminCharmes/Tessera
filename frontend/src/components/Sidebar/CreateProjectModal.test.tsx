import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CreateProjectModal from "./CreateProjectModal";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    projects: {
      create: vi.fn(),
      createFromTemplate: vi.fn(),
    },
  },
}));

const mockCreate = vi.mocked(api.projects.create);
const mockCreateFromTemplate = vi.mocked(api.projects.createFromTemplate);

const mockProject = {
  id: "mon-projet",
  name: "mon-projet",
  path: "/ws/projet",
  description: "Un projet",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

const mockResult = {
  project: mockProject,
  agents_created: [],
  repository_ready: true,
};
const mockResultWithAgents = {
  project: mockProject,
  agents_created: ["redacteur", "planificateur"],
  repository_ready: true,
};

describe("CreateProjectModal", () => {
  const onClose = vi.fn();
  const onCreated = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders form with name, description, and action buttons", () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    expect(screen.getByLabelText(/nom/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /créer/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /annuler/i }),
    ).toBeInTheDocument();
  });

  it("shows validation error when name is empty", async () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le nom est requis",
    );
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("shows validation error when name contains spaces", async () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent("d'espaces");
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("calls api.projects.create with name and description on valid submit", async () => {
    mockCreate.mockResolvedValue(mockResult);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    await userEvent.type(screen.getByLabelText(/description/i), "Un projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith("mon-projet", "Un projet");
    });
  });

  it("shows success message after project creation", async () => {
    mockCreate.mockResolvedValue(mockResult);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(
      await screen.findByText(/Projet.*mon-projet.*créé/i),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /continuer/i }),
    ).toBeInTheDocument();
  });

  it("does not show agents section when agents_created is empty", async () => {
    mockCreate.mockResolvedValue(mockResult);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await screen.findByText(/Projet.*mon-projet.*créé/i);
    expect(
      screen.queryByText(/agent.*créé.*automatiquement/i),
    ).not.toBeInTheDocument();
  });

  it("shows auto-created agents in success message", async () => {
    mockCreate.mockResolvedValue(mockResultWithAgents);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(
      await screen.findByText(/2 agents créés automatiquement/i),
    ).toBeInTheDocument();
    expect(screen.getByText(/redacteur, planificateur/i)).toBeInTheDocument();
  });

  it("calls onCreated with the project when Continuer is clicked", async () => {
    mockCreate.mockResolvedValue(mockResult);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await screen.findByRole("button", { name: /continuer/i });
    fireEvent.click(screen.getByRole("button", { name: /continuer/i }));

    expect(onCreated).toHaveBeenCalledWith(mockProject);
  });

  it("disables the submit button while loading", async () => {
    let resolve!: (r: typeof mockResult) => void;
    mockCreate.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(screen.getByRole("button", { name: /créer/i })).toBeDisabled();

    resolve(mockResult);
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: /continuer/i }),
      ).toBeInTheDocument(),
    );
  });

  it("displays API error when creation fails", async () => {
    mockCreate.mockRejectedValue(new Error("API 409: Project already exists"));

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "API 409: Project already exists",
    );
    expect(onCreated).not.toHaveBeenCalled();
  });

  it("calls onClose when Annuler is clicked", () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    fireEvent.click(screen.getByRole("button", { name: /annuler/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking the overlay backdrop before creation", () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    fireEvent.click(screen.getByRole("dialog"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onCreated when clicking overlay backdrop after success", async () => {
    mockCreate.mockResolvedValue(mockResult);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await screen.findByRole("button", { name: /continuer/i });
    fireEvent.click(screen.getByRole("dialog"));

    expect(onCreated).toHaveBeenCalledWith(mockProject);
  });

  it("annonce que le depot git est pret", async () => {
    // ticket-104 : sans depot a sa racine, un projet cree est inutilisable
    // par le pipeline — GitWorkspaceService leve NotAGitRepository et le run
    // s'arrete avant la premiere branche (ADR-024). L'utilisateur doit le
    // savoir a la creation, pas au premier run.
    vi.mocked(api.projects.create).mockResolvedValue(mockResult);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await screen.findByRole("button", { name: /continuer/i });
    expect(screen.getByText(/dépôt git initialisé/i)).toBeInTheDocument();
  });

  it("dit quoi faire quand l'initialisation du depot a echoue", async () => {
    vi.mocked(api.projects.create).mockResolvedValue({
      ...mockResult,
      repository_ready: false,
    });

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await screen.findByRole("button", { name: /continuer/i });
    // Un echec qui ne dit pas quoi faire laisse l'utilisateur devant un projet
    // cree mais inerte : la section Git de la barre laterale est le rattrapage.
    expect(screen.getByText(/section git/i)).toBeInTheDocument();
  });

  it("calls onClose when pressing Escape before creation", () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  describe("template mode", () => {
    const mockTemplateResult = {
      project: mockProject,
      backend_port: 8022,
      frontend_port: 5192,
      git_ready: true,
    };

    async function selectTemplate() {
      fireEvent.click(
        screen.getByRole("radio", { name: /gabarit fastapi \+ react/i }),
      );
    }

    it("calls createFromTemplate (not create) when template is selected", async () => {
      mockCreateFromTemplate.mockResolvedValue(mockTemplateResult);

      render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);
      await selectTemplate();
      await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
      fireEvent.click(screen.getByRole("button", { name: /créer/i }));

      await waitFor(() => {
        expect(mockCreateFromTemplate).toHaveBeenCalledWith(
          "mon-projet",
          "mon-projet",
        );
        expect(mockCreate).not.toHaveBeenCalled();
      });
    });

    it("displays assigned ports after template creation", async () => {
      mockCreateFromTemplate.mockResolvedValue(mockTemplateResult);

      render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);
      await selectTemplate();
      await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
      fireEvent.click(screen.getByRole("button", { name: /créer/i }));

      await screen.findByText(/continuer/i);
      expect(screen.getByText(/8022/)).toBeInTheDocument();
      expect(screen.getByText(/5192/)).toBeInTheDocument();
    });

    it("lowercases the project id like an empty project", async () => {
      mockCreateFromTemplate.mockResolvedValue(mockTemplateResult);

      render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);
      await selectTemplate();
      await userEvent.type(screen.getByLabelText(/nom/i), "MonProjet");
      fireEvent.click(screen.getByRole("button", { name: /créer/i }));

      await waitFor(() => {
        expect(mockCreateFromTemplate).toHaveBeenCalledWith("monprojet", "MonProjet");
      });
    });

    it("warns when the git repository could not be initialised", async () => {
      mockCreateFromTemplate.mockResolvedValue({
        ...mockTemplateResult,
        git_ready: false,
      });

      render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);
      await selectTemplate();
      await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
      fireEvent.click(screen.getByRole("button", { name: /créer/i }));

      await screen.findByText(/continuer/i);
      expect(screen.getByText(/n.a pas pu être initialisé/)).toBeInTheDocument();
    });

    it("shows remaining steps after template creation", async () => {
      mockCreateFromTemplate.mockResolvedValue(mockTemplateResult);

      render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);
      await selectTemplate();
      await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
      fireEvent.click(screen.getByRole("button", { name: /créer/i }));

      await screen.findByText(/continuer/i);
      expect(screen.getByText(/CLAUDE\.md/)).toBeInTheDocument();
      expect(screen.getByText(/dépôt GitHub/i)).toBeInTheDocument();
    });

    it("calls create (not createFromTemplate) when empty project is selected", async () => {
      mockCreate.mockResolvedValue(mockResult);

      render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);
      // "Projet vide" est sélectionné par défaut
      await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
      fireEvent.click(screen.getByRole("button", { name: /créer/i }));

      await waitFor(() => {
        expect(mockCreate).toHaveBeenCalledWith("mon-projet", "");
        expect(mockCreateFromTemplate).not.toHaveBeenCalled();
      });
    });
  });
});
