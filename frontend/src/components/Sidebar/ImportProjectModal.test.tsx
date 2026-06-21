import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ImportProjectModal from "./ImportProjectModal";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    projects: {
      import: vi.fn(),
      clone: vi.fn(),
      analyze: vi.fn(),
    },
    agents: {
      list: vi.fn(),
    },
  },
}));

const mockImport = vi.mocked(api.projects.import);
const mockClone = vi.mocked(api.projects.clone);
const mockAnalyze = vi.mocked(api.projects.analyze);
const mockAgentsList = vi.mocked(api.agents.list);

const mockProject = {
  id: "mon-projet",
  name: "mon-projet",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

const mockGithubProject = {
  ...mockProject,
  id: "my-repo",
  name: "my-repo",
  github_remote: "https://github.com/owner/my-repo",
};

const mockAnalysis = {
  claude_md: "# CLAUDE.md — mon-projet\nStack : TypeScript, React",
  detected_stack: ["TypeScript", "React"],
  suggested_agents: ["codeur", "reviewer", "testeur"],
  claude_md_written: true,
};

describe("ImportProjectModal", () => {
  const onClose = vi.fn();
  const onProjectCreated = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockAgentsList.mockResolvedValue([
      {
        role: "codeur",
        description: null,
        is_builtin: true,
        prompt_preview: "",
      },
      {
        role: "reviewer",
        description: null,
        is_builtin: true,
        prompt_preview: "",
      },
    ]);
  });

  // ------------------------------------------------------------------
  // Source type toggle
  // ------------------------------------------------------------------

  it("renders source type toggle with local selected by default", () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    expect(
      screen.getByRole("button", { name: /dossier local/i }),
    ).toHaveAttribute("aria-pressed", "true");
    expect(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    ).toHaveAttribute("aria-pressed", "false");
  });

  it("switches to GitHub URL input when clicking 'Cloner depuis GitHub'", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );

    expect(screen.getByLabelText(/url du repo github/i)).toBeInTheDocument();
    expect(
      screen.queryByLabelText(/chemin du dossier/i),
    ).not.toBeInTheDocument();
  });

  it("shows Cloner button label when GitHub source is selected", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );

    expect(
      screen.getByRole("button", { name: /cloner →/i }),
    ).toBeInTheDocument();
  });

  // ------------------------------------------------------------------
  // Local import (existing behaviour preserved)
  // ------------------------------------------------------------------

  it("renders step 1 with path input, mode selector, and action buttons", () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    expect(screen.getByLabelText(/chemin du dossier/i)).toBeInTheDocument();
    expect(screen.getByRole("radio", { name: /symlink/i })).toBeChecked();
    expect(screen.getByRole("radio", { name: /copie/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /importer/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /annuler/i }),
    ).toBeInTheDocument();
  });

  it("shows validation error when local path is empty", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /chemin.*requis/i,
    );
    expect(mockImport).not.toHaveBeenCalled();
  });

  it("calls api.projects.import then api.projects.analyze on valid local submit", async () => {
    mockImport.mockResolvedValue({ project: mockProject });
    mockAnalyze.mockResolvedValue(mockAnalysis);

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.type(
      screen.getByLabelText(/chemin du dossier/i),
      "/Users/moi/Desktop/mon-projet",
    );
    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    await waitFor(() => {
      expect(mockImport).toHaveBeenCalledWith({
        source_path: "/Users/moi/Desktop/mon-projet",
        mode: "symlink",
      });
    });
    await waitFor(() => {
      expect(mockAnalyze).toHaveBeenCalledWith("mon-projet", false);
    });
  });

  it("shows review step with CLAUDE.md and agents after local import success", async () => {
    mockImport.mockResolvedValue({ project: mockProject });
    mockAnalyze.mockResolvedValue(mockAnalysis);

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.type(
      screen.getByLabelText(/chemin du dossier/i),
      "/Users/moi/Desktop/mon-projet",
    );
    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    await waitFor(() => {
      expect(screen.getByText(/mon-projet importé/i)).toBeInTheDocument();
    });

    expect(screen.getByText(/# CLAUDE\.md — mon-projet/i)).toBeInTheDocument();
    expect(screen.getByText(/Stack détectée/i)).toBeInTheDocument();
  });

  it("marks registered agents with a check and absent agents with a warning", async () => {
    mockImport.mockResolvedValue({ project: mockProject });
    mockAnalyze.mockResolvedValue(mockAnalysis);

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/chemin du dossier/i), "/path");
    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    await waitFor(() =>
      expect(screen.getByText(/mon-projet importé/i)).toBeInTheDocument(),
    );

    expect(screen.getAllByText("✅").length).toBeGreaterThanOrEqual(2);
    expect(
      screen.getByRole("button", { name: /créer.*testeur/i }),
    ).toBeInTheDocument();
  });

  it("calls onProjectCreated and closes on Valider", async () => {
    mockImport.mockResolvedValue({ project: mockProject });
    mockAnalyze.mockResolvedValue(mockAnalysis);

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/chemin du dossier/i), "/path");
    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    await waitFor(() =>
      expect(screen.getByText(/mon-projet importé/i)).toBeInTheDocument(),
    );

    await userEvent.click(
      screen.getByRole("button", { name: /valider et ouvrir/i }),
    );

    expect(onProjectCreated).toHaveBeenCalledWith(mockProject);
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("shows error on import failure", async () => {
    mockImport.mockRejectedValue(new Error("API 409: Projet déjà importé"));

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/chemin du dossier/i), "/path");
    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "API 409: Projet déjà importé",
      );
    });
  });

  it("shows error on analyze failure", async () => {
    mockImport.mockResolvedValue({ project: mockProject });
    mockAnalyze.mockRejectedValue(new Error("API 502: LLM error"));

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/chemin du dossier/i), "/path");
    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("API 502: LLM error");
    });
  });

  it("calls onClose when Annuler is clicked in step 1", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /annuler/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking the overlay backdrop", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(screen.getByRole("dialog"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when pressing Escape", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.keyboard("{Escape}");

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("allows switching mode to Copie before import", async () => {
    mockImport.mockResolvedValue({ project: mockProject });
    mockAnalyze.mockResolvedValue(mockAnalysis);

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(screen.getByRole("radio", { name: /copie/i }));
    await userEvent.type(screen.getByLabelText(/chemin du dossier/i), "/path");
    await userEvent.click(screen.getByRole("button", { name: /importer/i }));

    await waitFor(() => {
      expect(mockImport).toHaveBeenCalledWith({
        source_path: "/path",
        mode: "copy",
      });
    });
  });

  // ------------------------------------------------------------------
  // GitHub clone flow
  // ------------------------------------------------------------------

  it("shows URL validation error when GitHub URL is empty", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );
    await userEvent.click(screen.getByRole("button", { name: /cloner →/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(/url.*requise/i);
    expect(mockClone).not.toHaveBeenCalled();
  });

  it("shows URL validation error for non-github.com URL", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );
    await userEvent.type(
      screen.getByLabelText(/url du repo github/i),
      "https://gitlab.com/owner/repo",
    );
    await userEvent.click(screen.getByRole("button", { name: /cloner →/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      /format invalide/i,
    );
    expect(mockClone).not.toHaveBeenCalled();
  });

  it("calls api.projects.clone with valid GitHub URL then analyze", async () => {
    mockClone.mockResolvedValue({
      project: mockGithubProject,
      claude_md_generated: true,
      detected_stack: ["Python"],
    });
    mockAnalyze.mockResolvedValue({
      ...mockAnalysis,
      claude_md: "# CLAUDE.md — my-repo",
    });

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );
    await userEvent.type(
      screen.getByLabelText(/url du repo github/i),
      "https://github.com/owner/my-repo",
    );
    await userEvent.click(screen.getByRole("button", { name: /cloner →/i }));

    await waitFor(() => {
      expect(mockClone).toHaveBeenCalledWith({
        repo_url: "https://github.com/owner/my-repo",
      });
    });
    await waitFor(() => {
      expect(mockAnalyze).toHaveBeenCalledWith("my-repo", false);
    });
  });

  it("shows review step after successful GitHub clone", async () => {
    mockClone.mockResolvedValue({
      project: mockGithubProject,
      claude_md_generated: true,
      detected_stack: ["Python", "FastAPI"],
    });
    mockAnalyze.mockResolvedValue({
      ...mockAnalysis,
      claude_md: "# CLAUDE.md — my-repo",
      detected_stack: ["Python", "FastAPI"],
    });

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );
    await userEvent.type(
      screen.getByLabelText(/url du repo github/i),
      "https://github.com/owner/my-repo",
    );
    await userEvent.click(screen.getByRole("button", { name: /cloner →/i }));

    await waitFor(() => {
      expect(screen.getByText(/my-repo importé/i)).toBeInTheDocument();
    });
    expect(screen.getByText(/Stack détectée/i)).toBeInTheDocument();
  });

  it("shows error on clone failure", async () => {
    mockClone.mockRejectedValue(new Error("API 422: git clone a échoué"));

    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );
    await userEvent.type(
      screen.getByLabelText(/url du repo github/i),
      "https://github.com/owner/my-repo",
    );
    await userEvent.click(screen.getByRole("button", { name: /cloner →/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "API 422: git clone a échoué",
      );
    });
  });

  it("clears URL validation error when switching back to local", async () => {
    render(
      <ImportProjectModal
        onClose={onClose}
        onProjectCreated={onProjectCreated}
      />,
    );

    await userEvent.click(
      screen.getByRole("button", { name: /cloner depuis github/i }),
    );
    await userEvent.click(screen.getByRole("button", { name: /cloner →/i }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();

    await userEvent.click(
      screen.getByRole("button", { name: /dossier local/i }),
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
