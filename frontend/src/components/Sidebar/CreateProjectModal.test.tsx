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
    mockCreate.mockResolvedValue(mockProject);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    await userEvent.type(screen.getByLabelText(/description/i), "Un projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith("mon-projet", "Un projet");
    });
  });

  it("calls onCreated with the new project after successful creation", async () => {
    mockCreate.mockResolvedValue(mockProject);

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith(mockProject);
    });
  });

  it("disables the submit button while loading", async () => {
    let resolve!: (p: typeof mockProject) => void;
    mockCreate.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );

    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/nom/i), "mon-projet");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(screen.getByRole("button", { name: /créer/i })).toBeDisabled();

    resolve(mockProject);
    await waitFor(() => expect(onCreated).toHaveBeenCalled());
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

  it("calls onClose when clicking the overlay backdrop", () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    fireEvent.click(screen.getByRole("dialog"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when pressing Escape", () => {
    render(<CreateProjectModal onClose={onClose} onCreated={onCreated} />);

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
