import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import CreateTicketModal from "./CreateTicketModal";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    tickets: {
      create: vi.fn(),
    },
  },
}));

const mockCreate = vi.mocked(api.tickets.create);

const mockTicket = {
  id: "ticket-016",
  title: "Ma feature",
  type: "feat" as const,
  status: "todo" as const,
  priority: "medium" as const,
  agent: "codeur",
  depends_on: [],
  created: "2026-06-20",
  github_issue_url: null,
  pr_number: null,
  body: "",
  project_id: "ide-core",
  file_path: "/tmp/ticket-016-ma-feature.md",
};

describe("CreateTicketModal", () => {
  const onClose = vi.fn();
  const onCreated = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders title, type, priority, description fields and action buttons", () => {
    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    expect(screen.getByLabelText(/titre/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/type/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/priorité/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /créer/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /annuler/i }),
    ).toBeInTheDocument();
  });

  it("shows validation error when title is empty", async () => {
    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Le titre est requis",
    );
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it("calls api.tickets.create with correct payload on valid submit", async () => {
    mockCreate.mockResolvedValue(mockTicket);

    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/titre/i), "Ma feature");
    await userEvent.selectOptions(screen.getByLabelText(/type/i), "fix");
    await userEvent.selectOptions(screen.getByLabelText(/priorité/i), "high");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith("ide-core", {
        title: "Ma feature",
        type: "fix",
        priority: "high",
        description: "",
      });
    });
  });

  it("calls onCreated with the new ticket after successful creation", async () => {
    mockCreate.mockResolvedValue(mockTicket);

    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/titre/i), "Ma feature");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith(mockTicket);
    });
  });

  it("disables submit button while loading", async () => {
    let resolve!: (t: typeof mockTicket) => void;
    mockCreate.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );

    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/titre/i), "Ma feature");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(screen.getByRole("button", { name: /créer/i })).toBeDisabled();

    resolve(mockTicket);
    await waitFor(() => expect(onCreated).toHaveBeenCalled());
  });

  it("displays API error when creation fails", async () => {
    mockCreate.mockRejectedValue(new Error("API 500: Internal Server Error"));

    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/titre/i), "Ma feature");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "API 500: Internal Server Error",
    );
    expect(onCreated).not.toHaveBeenCalled();
  });

  it("calls onClose when Annuler is clicked", () => {
    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /annuler/i }));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking the overlay backdrop", () => {
    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    fireEvent.click(screen.getByRole("dialog"));

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when pressing Escape", () => {
    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });

    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("trims whitespace from title before submitting", async () => {
    mockCreate.mockResolvedValue(mockTicket);

    render(
      <CreateTicketModal
        projectId="ide-core"
        onClose={onClose}
        onCreated={onCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/titre/i), "  Ma feature  ");
    fireEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        "ide-core",
        expect.objectContaining({ title: "Ma feature" }),
      );
    });
  });
});
