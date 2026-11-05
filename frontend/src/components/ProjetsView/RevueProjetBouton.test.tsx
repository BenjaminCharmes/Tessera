import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RevueProjetBouton from "./RevueProjetBouton";
import { api } from "../../lib/api";
import type { ProjectOverview } from "../../types/api";

vi.mock("../../lib/api", () => ({
  api: { orchestrator: { run: vi.fn(), limits: vi.fn() } },
}));

const run = vi.mocked(api.orchestrator.run);
const limits = vi.mocked(api.orchestrator.limits);

function projet(extra: Partial<ProjectOverview> = {}): ProjectOverview {
  return {
    id: "serpent",
    name: "Serpent",
    category: null,
    description: "",
    github_remote: null,
    created_at: "2026-09-01T10:00:00Z",
    last_activity: null,
    tickets: { todo: 0, in_progress: 0, in_review: 0, blocked: 0, done: 1 },
    run_actif: false,
    icon: false,
    services_declares: false,
    services_en_cours: false,
    online_declared: false,
    ...extra,
  };
}

const OUVRIR = { name: "Revue du projet" };

describe("RevueProjetBouton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    limits.mockResolvedValue({ run_max_budget_usd: 5, llm_max_budget_usd: 1 });
    run.mockResolvedValue({ run_id: "r1", ticket_id: "ticket-900" });
  });

  it("shows the estimated cost and the cap before the confirmation", async () => {
    render(<RevueProjetBouton projet={projet()} onLancee={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", OUVRIR));
    expect(await screen.findByText(/Coût estimé/)).toHaveTextContent("3.00 $");
    expect(screen.getByText(/Plafond de la revue/)).toHaveTextContent("3.00 $");
    expect(run).not.toHaveBeenCalled();
  });

  it("caps the estimate at the run cap when it is lower", async () => {
    limits.mockResolvedValue({ run_max_budget_usd: 1.5, llm_max_budget_usd: 1 });
    render(<RevueProjetBouton projet={projet()} onLancee={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", OUVRIR));
    expect(await screen.findByText(/Coût estimé/)).toHaveTextContent("1.50 $");
  });

  it("starts a review run once the user confirms", async () => {
    const onLancee = vi.fn();
    render(<RevueProjetBouton projet={projet()} onLancee={onLancee} />);
    await userEvent.click(screen.getByRole("button", OUVRIR));
    await userEvent.click(await screen.findByRole("button", { name: "Lancer la revue" }));
    await waitFor(() => expect(onLancee).toHaveBeenCalled());
    expect(run).toHaveBeenCalledWith({ project_id: "serpent", mode: "revue" });
  });

  it("sends no launch request when the confirmation is cancelled", async () => {
    render(<RevueProjetBouton projet={projet()} onLancee={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", OUVRIR));
    await userEvent.click(await screen.findByRole("button", { name: "Annuler" }));
    expect(run).not.toHaveBeenCalled();
    expect(screen.queryByText(/Coût estimé/)).toBeNull();
  });

  it("names the running ticket on a 409 and disables the button", async () => {
    run.mockRejectedValue(
      new Error("API 409: Un pipeline tourne déjà sur le projet 'serpent' (ticket-042)."),
    );
    render(<RevueProjetBouton projet={projet()} onLancee={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", OUVRIR));
    await userEvent.click(await screen.findByRole("button", { name: "Lancer la revue" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("ticket-042");
    expect(screen.getByRole("button", OUVRIR)).toBeDisabled();
  });

  it("disables the button while a run holds the project", () => {
    render(<RevueProjetBouton projet={projet({ run_actif: true })} onLancee={vi.fn()} />);
    expect(screen.getByRole("button", OUVRIR)).toBeDisabled();
  });

  it("reports a failed estimate and sends no launch request", async () => {
    limits.mockRejectedValue(new Error("API 500: boom"));
    render(<RevueProjetBouton projet={projet()} onLancee={vi.fn()} />);
    await userEvent.click(screen.getByRole("button", OUVRIR));
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
    expect(run).not.toHaveBeenCalled();
  });
});
