import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Editor from "./index";
import { readFile } from "../../lib/fs";
import { api } from "../../lib/api";
import type { Ticket, TicketRunSummary } from "../../types/api";

// Ticket-332 : les tests rendent l'éditeur entier, l'écran où le bouton doit
// apparaître. Celui du ticket-327 vérifiait un composant que rien n'affichait.

vi.mock("@monaco-editor/react", () => ({
  default: ({ value }: { value: string }) => <pre data-testid="monaco">{value}</pre>,
}));
vi.mock("../../lib/fs", () => ({ readFile: vi.fn() }));
vi.mock("../../lib/api");

const ticket = {
  id: "ticket-042",
  project_id: "ide-core",
  title: "Une fonctionnalité",
  file_path: "/w/projects/ide-core/tickets/done/ticket-042.md",
} as Ticket;

function run(over: Partial<TicketRunSummary>): TicketRunSummary {
  return {
    id: "run-1",
    started_at: "2026-10-03T17:19:08+00:00",
    finished_at: "2026-10-03T17:33:00+00:00",
    rounds: 1,
    approved: true,
    final_status: "done",
    total_cost_usd: 0.87,
    arret: null,
    ...over,
  };
}

beforeEach(() => {
  vi.mocked(readFile).mockReset().mockResolvedValue("# ticket-042 — Contenu du ticket");
  vi.mocked(api.tickets.runs).mockReset();
  vi.mocked(api.runs.events).mockReset().mockResolvedValue([]);
});

describe("Editor — runs d'un ticket (ticket-332)", () => {
  it("offers to replay a finished run, opens it in place of the ticket, and comes back", async () => {
    vi.mocked(api.tickets.runs).mockResolvedValue([run({ id: "run-abc" })]);
    render(<Editor ticket={ticket} />);

    await userEvent.click(await screen.findByRole("button", { name: "Revoir le run" }));

    expect(api.tickets.runs).toHaveBeenCalledWith("ide-core", "ticket-042");
    expect(api.runs.events).toHaveBeenCalledWith("run-abc");
    expect(screen.getByText("Run ticket-042")).toBeInTheDocument();
    expect(screen.queryByText("ticket-042 — Contenu du ticket")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /Retour au ticket/ }));

    expect(await screen.findByText("ticket-042 — Contenu du ticket")).toBeInTheDocument();
  });

  it("does not offer a run that has not finished", async () => {
    // Enveloppe de file ou run en cours : rien à relire.
    vi.mocked(api.tickets.runs).mockResolvedValue([run({ finished_at: null })]);
    render(<Editor ticket={ticket} />);

    await screen.findByText("ticket-042 — Contenu du ticket");
    await vi.waitFor(() => expect(api.tickets.runs).toHaveBeenCalled());
    expect(screen.queryByRole("button", { name: "Revoir le run" })).not.toBeInTheDocument();
  });

  it("shows no run strip for a file opened from the tree", async () => {
    vi.mocked(api.tickets.runs).mockResolvedValue([run({})]);
    render(<Editor ticket={ticket} openFilePath="/w/a.py" />);

    await screen.findByTestId("monaco");
    expect(api.tickets.runs).not.toHaveBeenCalled();
    expect(screen.queryByRole("button", { name: "Revoir le run" })).not.toBeInTheDocument();
  });

  it("shows the three latest runs and folds the others behind a button (ticket-333)", async () => {
    const runs = Array.from({ length: 8 }, (_, i) => run({ id: `run-${i}` }));
    vi.mocked(api.tickets.runs).mockResolvedValue(runs);
    render(<Editor ticket={ticket} />);

    await screen.findAllByRole("button", { name: "Revoir le run" });
    expect(screen.getAllByRole("button", { name: "Revoir le run" })).toHaveLength(3);

    await userEvent.click(screen.getByRole("button", { name: "Afficher les 5 autres" }));
    expect(screen.getAllByRole("button", { name: "Revoir le run" })).toHaveLength(8);

    await userEvent.click(screen.getByRole("button", { name: "Masquer" }));
    expect(screen.getAllByRole("button", { name: "Revoir le run" })).toHaveLength(3);
  });
});
