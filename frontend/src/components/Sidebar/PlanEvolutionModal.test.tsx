import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import PlanEvolutionModal from "./PlanEvolutionModal";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    projects: {
      plan: vi.fn(),
    },
    tickets: {
      batch: vi.fn(),
    },
  },
}));

const mockPlan = vi.mocked(api.projects.plan);
const mockBatch = vi.mocked(api.tickets.batch);

const MOCK_DRAFTS = [
  {
    title: "Configurer OAuth (backend)",
    type: "feat",
    priority: "high",
    agent: "codeur",
    description: "Mettre en place le flow OAuth côté serveur.",
    acceptance_criteria: ["Token validé", "Session créée"],
    depends_on_index: [],
  },
  {
    title: "Page de connexion (frontend)",
    type: "feat",
    priority: "high",
    agent: "codeur",
    description: "Bouton de connexion sur la page de login.",
    acceptance_criteria: ["Bouton visible"],
    depends_on_index: [0],
  },
  {
    title: "Tests E2E auth",
    type: "chore",
    priority: "low",
    agent: "codeur",
    description: "Tests end-to-end du flow auth.",
    acceptance_criteria: ["Flow validé"],
    depends_on_index: [1],
  },
];

const MOCK_PLAN_RESULT = {
  drafts: MOCK_DRAFTS,
  summary: "Auth OAuth en 3 tickets",
};

const MOCK_CREATED_TICKETS = [
  {
    id: "ticket-042",
    title: "Configurer OAuth (backend)",
    type: "feat" as const,
    status: "todo" as const,
    priority: "high" as const,
    agent: "codeur",
    depends_on: [],
    created: "2026-06-21",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "ide-core",
    file_path: "/tmp/ticket-042.md",
  },
  {
    id: "ticket-043",
    title: "Page de connexion (frontend)",
    type: "feat" as const,
    status: "todo" as const,
    priority: "high" as const,
    agent: "codeur",
    depends_on: ["ticket-042"],
    created: "2026-06-21",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "ide-core",
    file_path: "/tmp/ticket-043.md",
  },
];

describe("PlanEvolutionModal", () => {
  const onClose = vi.fn();
  const onBatchCreated = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ------------------------------------------------------------------
  // Step 1 — description
  // ------------------------------------------------------------------

  it("renders description textarea and Planifier button", () => {
    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /planifier/i }),
    ).toBeInTheDocument();
  });

  it("Planifier button is disabled when description is empty", () => {
    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    expect(screen.getByRole("button", { name: /planifier/i })).toBeDisabled();
  });

  it("Planifier button is enabled after typing a description", async () => {
    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    await userEvent.type(
      screen.getByLabelText(/description/i),
      "Ajouter OAuth",
    );
    expect(
      screen.getByRole("button", { name: /planifier/i }),
    ).not.toBeDisabled();
  });

  it("calls api.projects.plan with correct payload on submit", async () => {
    mockPlan.mockResolvedValue(MOCK_PLAN_RESULT);

    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    await userEvent.type(
      screen.getByLabelText(/description/i),
      "Ajouter OAuth Google",
    );
    fireEvent.click(screen.getByRole("button", { name: /planifier/i }));

    await waitFor(() => {
      expect(mockPlan).toHaveBeenCalledWith("ide-core", "Ajouter OAuth Google");
    });
  });

  it("shows error message when plan call fails", async () => {
    mockPlan.mockRejectedValue(new Error("API 502: Planner error"));

    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    await userEvent.type(screen.getByLabelText(/description/i), "Test");
    fireEvent.click(screen.getByRole("button", { name: /planifier/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "API 502: Planner error",
    );
  });

  it("calls onClose when Annuler is clicked", () => {
    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /annuler/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when pressing Escape", () => {
    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking the overlay backdrop", () => {
    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );

    fireEvent.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  // ------------------------------------------------------------------
  // Step 2 — review drafts
  // ------------------------------------------------------------------

  async function renderAtStep2() {
    mockPlan.mockResolvedValue(MOCK_PLAN_RESULT);
    render(
      <PlanEvolutionModal
        projectId="ide-core"
        onClose={onClose}
        onBatchCreated={onBatchCreated}
      />,
    );
    await userEvent.type(screen.getByLabelText(/description/i), "OAuth");
    fireEvent.click(screen.getByRole("button", { name: /planifier/i }));
    await waitFor(() =>
      expect(screen.getByText("Auth OAuth en 3 tickets")).toBeInTheDocument(),
    );
  }

  it("shows draft tickets after planning", async () => {
    await renderAtStep2();
    expect(screen.getByText("Configurer OAuth (backend)")).toBeInTheDocument();
    expect(
      screen.getByText("Page de connexion (frontend)"),
    ).toBeInTheDocument();
    expect(screen.getByText("Tests E2E auth")).toBeInTheDocument();
  });

  it("shows the plan summary", async () => {
    await renderAtStep2();
    expect(screen.getByText("Auth OAuth en 3 tickets")).toBeInTheDocument();
  });

  it("all checkboxes are checked by default", async () => {
    await renderAtStep2();
    const checkboxes = screen.getAllByRole("checkbox");
    expect(checkboxes).toHaveLength(3);
    checkboxes.forEach((cb) => expect(cb).toBeChecked());
  });

  it("can deselect a ticket by unchecking its checkbox", async () => {
    await renderAtStep2();
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[2]);
    expect(checkboxes[2]).not.toBeChecked();
  });

  it("Créer button shows count of selected tickets", async () => {
    await renderAtStep2();
    expect(
      screen.getByRole("button", { name: /créer 3 tickets/i }),
    ).toBeInTheDocument();
  });

  it("Créer button updates count when a ticket is deselected", async () => {
    await renderAtStep2();
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);
    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /créer 2 tickets/i }),
      ).toBeInTheDocument();
    });
  });

  it("Retour button goes back to step 1", async () => {
    await renderAtStep2();
    fireEvent.click(screen.getByRole("button", { name: /retour/i }));
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument();
  });

  // ------------------------------------------------------------------
  // Batch creation
  // ------------------------------------------------------------------

  it("calls api.tickets.batch with all selected drafts", async () => {
    mockBatch.mockResolvedValue({ created: MOCK_CREATED_TICKETS });
    await renderAtStep2();

    fireEvent.click(screen.getByRole("button", { name: /créer 3 tickets/i }));

    await waitFor(() => {
      expect(mockBatch).toHaveBeenCalledWith("ide-core", MOCK_DRAFTS);
    });
  });

  it("calls onBatchCreated with the created tickets", async () => {
    mockBatch.mockResolvedValue({ created: MOCK_CREATED_TICKETS });
    await renderAtStep2();

    fireEvent.click(screen.getByRole("button", { name: /créer 3 tickets/i }));

    await waitFor(() => {
      expect(onBatchCreated).toHaveBeenCalledWith(MOCK_CREATED_TICKETS);
    });
  });

  it("filters and remaps depends_on_index when a ticket is deselected", async () => {
    mockBatch.mockResolvedValue({ created: MOCK_CREATED_TICKETS });
    await renderAtStep2();

    // Deselect ticket at index 0 (backend)
    const checkboxes = screen.getAllByRole("checkbox");
    fireEvent.click(checkboxes[0]);

    fireEvent.click(screen.getByRole("button", { name: /créer 2 tickets/i }));

    await waitFor(() => {
      const sentTickets = mockBatch.mock.calls[0][1];
      expect(sentTickets).toHaveLength(2);
      // Frontend (originally dep on index 0) → dep removed since 0 deselected
      expect(sentTickets[0].depends_on_index).toEqual([]);
      // E2E (originally dep on index 1) → remapped to index 0
      expect(sentTickets[1].depends_on_index).toEqual([0]);
    });
  });

  it("shows error message when batch creation fails", async () => {
    mockBatch.mockRejectedValue(new Error("API 500: Server error"));
    await renderAtStep2();

    fireEvent.click(screen.getByRole("button", { name: /créer 3 tickets/i }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "API 500: Server error",
    );
    expect(onBatchCreated).not.toHaveBeenCalled();
  });
});

describe("PlanEvolutionModal — ne pas perdre un appel payé", () => {
  it("ne se ferme pas au clic exterieur pendant la planification", async () => {
    const onClose = vi.fn();
    vi.mocked(api.projects.plan).mockReturnValue(new Promise(() => {}));

    render(<PlanEvolutionModal projectId="p" onClose={onClose} onBatchCreated={() => {}} />);
    await userEvent.type(screen.getByLabelText(/description/i), "une évolution");
    await userEvent.click(screen.getByRole("button", { name: /planifier/i }));

    await userEvent.click(screen.getByRole("dialog"));

    expect(onClose).not.toHaveBeenCalled();
  });

  it("ne se ferme pas au clic exterieur quand les brouillons sont a l'ecran", async () => {
    // Panne vecue : l'appel au planificateur est facture, et un clic a cote
    // jetait son resultat sans rien demander.
    const onClose = vi.fn();
    vi.mocked(api.projects.plan).mockResolvedValue({
      summary: "s",
      drafts: [
        {
          title: "T1", type: "feat", priority: "high", agent: "codeur",
          description: "d", acceptance_criteria: [], depends_on_index: [],
        },
      ],
    });

    render(<PlanEvolutionModal projectId="p" onClose={onClose} onBatchCreated={() => {}} />);
    await userEvent.type(screen.getByLabelText(/description/i), "une évolution");
    await userEvent.click(screen.getByRole("button", { name: /planifier/i }));
    await screen.findByText("T1");

    await userEvent.click(screen.getByRole("dialog"));

    expect(onClose).not.toHaveBeenCalled();
  });
});
