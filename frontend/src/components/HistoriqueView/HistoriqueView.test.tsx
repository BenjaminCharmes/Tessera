import { useState } from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import HistoriqueView from ".";
import RunHistory from "../Sidebar/RunHistory";
import { boutonsPleins } from "../../test/boutons";
import { OuvrirTicketContext } from "../../hooks/useOuvrirTicket";
import type { OuvrirTicket } from "../../hooks/useOuvrirTicket";
import type { PipelineRun, Project, Ticket } from "../../types/api";

// Le fil rejoué appelle l'API : une doublure suffit, on ne teste que le cadre.
vi.mock("../StatsView/RunHistorique", () => ({
  default: ({ runId }: { runId: string }) => <div data-testid="fil">{runId}</div>,
}));

function run(id: string, ticketId: string, extra: Partial<PipelineRun>): PipelineRun {
  return {
    id,
    ticket_id: ticketId,
    started_at: "2026-10-14T07:00:00Z",
    finished_at: "2026-10-14T07:10:00Z",
    rounds: 1,
    approved: true,
    final_status: "done",
    total_cost_usd: 1.5,
    ...extra,
  };
}

const RUNS: PipelineRun[] = [
  run("r-ancien", "ticket-10", { started_at: "2026-10-12T07:00:00Z", approved: false, final_status: "blocked", rounds: 3 }),
  run("r-recent", "ticket-11", { started_at: "2026-10-14T07:00:00Z" }),
  run("r-deux-tours", "ticket-12", { started_at: "2026-10-13T07:00:00Z", rounds: 2 }),
];

function ticket(id: string, title: string): Ticket {
  return {
    id,
    title,
    status: "done",
    type: "feat",
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-10-01T00:00:00Z",
    github_issue_url: null,
    pr_number: id === "ticket-11" ? 418 : null,
    body: "",
    project_id: "p1",
    file_path: "",
  };
}

const TICKETS = [
  ticket("ticket-10", "Titre dix"),
  ticket("ticket-11", "Titre onze"),
  ticket("ticket-12", "Titre douze"),
];

const PROJET: Project = {
  id: "p1",
  name: "P1",
  path: "/p1",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: "moi/depot",
};

/** La colonne et le centre partagent le run choisi, comme dans le cockpit. */
function Cockpit({ runs = RUNS, initial = null }: { runs?: PipelineRun[]; initial?: string | null }) {
  const [selectionne, setSelectionne] = useState<string | null>(initial);
  return (
    <>
      <aside aria-label="colonne">
        <RunHistory
          runs={runs}
          loading={false}
          error={null}
          selectedRunId={selectionne}
          onSelectRun={setSelectionne}
        />
      </aside>
      <main aria-label="centre">
        <HistoriqueView
          runs={runs}
          loading={false}
          error={null}
          runSelectionne={selectionne}
          onSelectRun={setSelectionne}
          tickets={TICKETS}
          project={PROJET}
        />
      </main>
    </>
  );
}

const centre = () => within(screen.getByRole("main", { name: "centre" }));
const colonne = () => within(screen.getByRole("complementary", { name: "colonne" }));

describe("HistoriqueView", () => {
  it("shows the clicked run of the column with its ticket and verdict", async () => {
    render(<Cockpit />);
    await userEvent.click(colonne().getByText("ticket-12"));
    expect(centre().getByRole("heading", { name: "Titre douze" })).toBeInTheDocument();
    expect(centre().getByText("Approuvé · 2 tours")).toBeInTheDocument();
    expect(centre().getByTestId("fil")).toHaveTextContent("r-deux-tours");
  });

  it("shows the most recent run when none is selected", () => {
    render(<Cockpit />);
    expect(centre().getByRole("heading", { name: "Titre onze" })).toBeInTheDocument();
    expect(centre().getByTestId("fil")).toHaveTextContent("r-recent");
    expect(centre().getByRole("link", { name: "PR #418" })).toHaveAttribute(
      "href",
      "https://github.com/moi/depot/pull/418",
    );
  });

  it("shows the empty state when the project has no run", () => {
    render(<Cockpit runs={[]} />);
    expect(centre().getByText("Aucun run sur ce projet")).toBeInTheDocument();
  });

  it("switches to every run and keeps only multi-round runs with the filter", async () => {
    render(<Cockpit />);
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    expect(centre().getByText("ticket-10")).toBeInTheDocument();
    expect(centre().getByText("ticket-11")).toBeInTheDocument();

    await userEvent.click(centre().getByRole("button", { name: "Plusieurs tours" }));
    expect(centre().getByText("ticket-10")).toBeInTheDocument();
    expect(centre().getByText("ticket-12")).toBeInTheDocument();
    expect(centre().queryByText("ticket-11")).not.toBeInTheDocument();
  });

  it("keeps only refused or blocked runs with the matching filter", async () => {
    render(<Cockpit />);
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    await userEvent.click(centre().getByRole("button", { name: "Refusés ou bloqués" }));
    expect(centre().getByText("ticket-10")).toBeInTheDocument();
    expect(centre().queryByText("ticket-11")).not.toBeInTheDocument();
  });

  it("opens the detail of the clicked table row", async () => {
    render(<Cockpit />);
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    await userEvent.click(centre().getByText("Titre dix"));
    expect(centre().getByRole("heading", { name: "Titre dix" })).toBeInTheDocument();
    expect(centre().getByText("Bloqué · 3 tours")).toBeInTheDocument();
    expect(centre().getByRole("button", { name: "Détail du run" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("shows one row per ticket for a queue, in the column and in the table", async () => {
    const file = run("r-file", "ticket-10", { started_at: "2026-10-14T06:00:00Z" });
    const enfants = [
      run("r-e1", "ticket-10", { parent_run_id: "r-file" }),
      run("r-e2", "ticket-11", { parent_run_id: "r-file" }),
    ];
    render(<Cockpit runs={[file, ...enfants]} />);
    expect(colonne().getAllByText(/^ticket-1\d$/)).toHaveLength(2);
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    expect(centre().getAllByText(/^ticket-1\d$/)).toHaveLength(2);
  });

  it("shows a single-ticket run once", async () => {
    render(<Cockpit runs={[run("r-seul", "ticket-10", { parent_run_id: null })]} />);
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    expect(centre().getAllByText("ticket-10")).toHaveLength(1);
  });

  it("shows an interrupted run as such, with a dash for the duration", async () => {
    const interrompu = run("r-int", "ticket-10", {
      approved: false,
      final_status: "blocked",
      rounds: 0,
      finished_at: "2026-10-15T07:00:00Z",
      arret: "backend restarted: the run's process is gone",
    });
    render(<Cockpit runs={[interrompu]} />);
    expect(centre().getByText("Interrompu")).toBeInTheDocument();
    expect(centre().getByText("Durée").nextElementSibling).toHaveTextContent("—");
    expect(centre().queryByText(/min/)).not.toBeInTheDocument();

    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    expect(centre().getByText("Interrompu")).toBeInTheDocument();
  });

  it("goes back to the detail when a run is picked in the column from the table", async () => {
    render(<Cockpit />);
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    await userEvent.click(colonne().getByText("ticket-12"));
    expect(centre().getByRole("heading", { name: "Titre douze" })).toBeInTheDocument();
  });
});

describe("HistoriqueView — composants communs (ticket-442)", () => {
  it("draws the verdict of the detail with the shared StatusPill", () => {
    render(<Cockpit initial="r-deux-tours" />);
    const verdict = centre().getByText("Approuvé · 2 tours");
    expect(verdict).toHaveAttribute("data-etat", "attention");
  });

  it("draws each verdict of the table with the shared StatusPill", async () => {
    render(<Cockpit />);
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));
    expect(centre().getByText("Bloqué")).toHaveAttribute("data-etat", "echec");
    expect(centre().getAllByText("Approuvé")[0]).toHaveAttribute("data-etat", "reussi");
  });

  it("has at most one plein button", () => {
    render(<Cockpit />);
    expect(boutonsPleins().length).toBeLessThanOrEqual(1);
  });
});

describe("HistoriqueView — un numéro de ticket ouvre le ticket (ticket-460)", () => {
  function avecAction() {
    const ouvrir = vi.fn<OuvrirTicket>().mockResolvedValue("ok");
    return {
      ouvrir,
      enveloppe: (initial: string | null = null) => (
        <OuvrirTicketContext.Provider value={ouvrir}>
          <Cockpit initial={initial} />
        </OuvrirTicketContext.Provider>
      ),
    };
  }

  it("opens the ticket of a table row, and keeps the table", async () => {
    const { ouvrir, enveloppe } = avecAction();
    render(enveloppe());
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));

    await userEvent.click(centre().getByRole("button", { name: "ticket-10" }));

    expect(ouvrir).toHaveBeenCalledWith("p1", "ticket-10");
    expect(centre().getByRole("button", { name: "Tous les runs" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("opens the ticket from the keyboard on a table row", async () => {
    const { ouvrir, enveloppe } = avecAction();
    render(enveloppe());
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));

    centre().getByRole("button", { name: "ticket-11" }).focus();
    await userEvent.keyboard("{Enter}");

    expect(ouvrir).toHaveBeenCalledWith("p1", "ticket-11");
  });

  it("still opens the run when the rest of the row is clicked", async () => {
    const { ouvrir, enveloppe } = avecAction();
    render(enveloppe());
    await userEvent.click(centre().getByRole("button", { name: "Tous les runs" }));

    await userEvent.click(centre().getByText("Titre douze"));

    expect(ouvrir).not.toHaveBeenCalled();
    expect(centre().getByRole("heading", { name: "Titre douze" })).toBeInTheDocument();
  });

  it("opens the ticket from the header of the run detail", async () => {
    const { ouvrir, enveloppe } = avecAction();
    render(enveloppe("r-deux-tours"));

    await userEvent.click(centre().getByRole("button", { name: "ticket-12" }));

    expect(ouvrir).toHaveBeenCalledWith("p1", "ticket-12");
  });
});
