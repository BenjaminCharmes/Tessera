import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CreateProjectModal from "./CreateProjectModal";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    projects: {
      create: vi.fn(),
    },
  },
}));

const mockCreate = vi.mocked(api.projects.create);

const mockProject = {
  id: "mon-projet",
  name: "mon-projet",
  description: "Un projet",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

const mockResult = { project: mockProject, agents_created: [] };
const mockResultWithAgents = {
  project: mockProject,
  agents_created: ["redacteur", "planificateur"],
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

  it("calls onClose when pressing Escape before creation", () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
