import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjetCarte from "./ProjetCarte";
import { idsAFaire } from "./idsAFaire";
import { api } from "../../lib/api";
import type { ProjectOverview, Ticket } from "../../types/api";

vi.mock("../../lib/api", () => ({
  api: {
    tickets: { list: vi.fn() },
    orchestrator: { run: vi.fn(), append: vi.fn() },
  },
}));

const list = vi.mocked(api.tickets.list);
const run = vi.mocked(api.orchestrator.run);
const append = vi.mocked(api.orchestrator.append);

function projet(extra: Partial<ProjectOverview> = {}): ProjectOverview {
  return {
    id: "serpent",
    name: "Serpent",
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-09-01T10:00:00Z",
    last_activity: null,
    tickets: { todo: 3, in_progress: 0, in_review: 0, blocked: 0, done: 1 },
    run_actif: false,
    icon: false,
    services_declares: false,
    services_en_cours: false,
    online_declared: false,
    ...extra,
  };
}

function ticket(id: string, status: Ticket["status"]): Ticket {
  return {
    id,
    title: id,
    type: "feat",
    status,
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-10-01",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "serpent",
    file_path: `${id}.md`,
  };
}

function afficher(
  p: ProjectOverview,
  surSelection = vi.fn(),
  surLancee = vi.fn(),
  fileEnCours: string | null = null,
) {
  render(
    <ProjetCarte
      projet={p}
      fileEnCours={fileEnCours}
      actif={false}
      categories={[]}
      onSelect={surSelection}
      onChangerCategorie={vi.fn()}
      onFileLancee={surLancee}
      onServicesChange={vi.fn()}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("LancerFile", () => {
  it("shows no queue button when the project has nothing to do", () => {
    afficher(projet({ tickets: { todo: 0, in_progress: 0, in_review: 0, blocked: 0, done: 4 } }));

    expect(screen.queryByRole("button", { name: /^File/ })).not.toBeInTheDocument();
  });

  it("disables the queue button and says why while a single-ticket run is open", () => {
    afficher(projet({ run_actif: true }));

    const bouton = screen.getByRole("button", { name: "File (3)" });
    expect(bouton).toBeDisabled();
    expect(bouton).toHaveAttribute("title", "Un run est en cours");
    expect(screen.getByText("Run en cours")).toBeInTheDocument();
  });

  it("offers to append the todo tickets when a queue is already running", async () => {
    list.mockResolvedValue({
      tickets: [ticket("ticket-7", "todo"), ticket("ticket-3", "todo")],
      unreadable: [],
    });
    append.mockResolvedValue({ ajoutes: ["ticket-3"], ignores: { "ticket-7": "déjà dans la file" }, refuses: {} });
    const surSelection = vi.fn();
    const surLancee = vi.fn();
    afficher(projet({ run_actif: true }), surSelection, surLancee, "run-42");

    await userEvent.click(screen.getByRole("button", { name: "Ajouter à la file (3)" }));
    expect(screen.getByText("Ajouter 3 tickets à la file en cours ?")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ajouter" }));

    await waitFor(() => expect(surLancee).toHaveBeenCalledTimes(1));
    expect(append).toHaveBeenCalledWith("run-42", ["ticket-3", "ticket-7"]);
    expect(run).not.toHaveBeenCalled();
    expect(screen.getByText("1 ajouté")).toHaveAttribute("role", "status");
    expect(surSelection).not.toHaveBeenCalled();
  });

  it("shows the backend message when the queue can no longer take tickets", async () => {
    list.mockResolvedValue({ tickets: [ticket("ticket-1", "todo")], unreadable: [] });
    append.mockRejectedValue(new Error("API 409: Ce run n'est pas une file en cours"));
    afficher(projet({ run_actif: true }), vi.fn(), vi.fn(), "run-42");

    await userEvent.click(screen.getByRole("button", { name: "Ajouter à la file (3)" }));
    await userEvent.click(screen.getByRole("button", { name: "Ajouter" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("La file en cours n'accepte plus de tickets.");
  });

  it("asks for confirmation on first click without launching or selecting the card", async () => {
    const surSelection = vi.fn();
    afficher(projet(), surSelection);

    await userEvent.click(screen.getByRole("button", { name: "File (3)" }));

    expect(screen.getByText("Lancer 3 tickets ?")).toBeInTheDocument();
    expect(run).not.toHaveBeenCalled();
    expect(list).not.toHaveBeenCalled();
    expect(surSelection).not.toHaveBeenCalled();
  });

  it("goes back to the button when the confirmation is cancelled", async () => {
    afficher(projet());
    await userEvent.click(screen.getByRole("button", { name: "File (3)" }));

    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));

    expect(screen.getByRole("button", { name: "File (3)" })).toBeInTheDocument();
    expect(run).not.toHaveBeenCalled();
  });

  it("sends a queue run with only the todo tickets sorted by id, then reloads", async () => {
    list.mockResolvedValue({
      tickets: [
        ticket("ticket-412", "todo"),
        ticket("ticket-9", "todo"),
        ticket("ticket-100", "done"),
        ticket("ticket-30", "todo"),
        ticket("ticket-50", "blocked"),
      ],
      unreadable: [],
    });
    run.mockResolvedValue({ run_id: "r1" });
    const surSelection = vi.fn();
    const surLancee = vi.fn();
    afficher(projet(), surSelection, surLancee);

    await userEvent.click(screen.getByRole("button", { name: "File (3)" }));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));

    await waitFor(() => expect(surLancee).toHaveBeenCalledTimes(1));
    expect(run).toHaveBeenCalledWith({
      project_id: "serpent",
      mode: "queue",
      ticket_ids: ["ticket-9", "ticket-30", "ticket-412"],
    });
    expect(surSelection).not.toHaveBeenCalled();
  });

  it("shows an error message when the backend answers 409", async () => {
    list.mockResolvedValue({ tickets: [ticket("ticket-1", "todo")], unreadable: [] });
    run.mockRejectedValue(new Error("API 409: run already open"));
    const surLancee = vi.fn();
    afficher(projet(), vi.fn(), surLancee);

    await userEvent.click(screen.getByRole("button", { name: "File (3)" }));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Un run est déjà en cours");
    expect(surLancee).not.toHaveBeenCalled();
  });

  it("shows the raw message for any other failure", async () => {
    list.mockRejectedValue(new Error("API 500: boom"));
    afficher(projet());

    await userEvent.click(screen.getByRole("button", { name: "File (3)" }));
    await userEvent.click(screen.getByRole("button", { name: "Lancer" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("API 500: boom");
  });
});

describe("idsAFaire", () => {
  it("keeps todo tickets and orders ids numerically", () => {
    const ids = idsAFaire([
      ticket("ticket-10", "todo"),
      ticket("ticket-2", "todo"),
      ticket("ticket-3", "done"),
    ]);

    expect(ids).toEqual(["ticket-2", "ticket-10"]);
  });
});
