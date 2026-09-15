import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../../lib/api";
import TicketActivity from "./TicketActivity";
import type { Ticket } from "../../types/api";

const ticket: Ticket = {
  id: "ticket-042",
  title: "Endpoint de santé",
  type: "feat",
  status: "todo",
  priority: "high",
  agent: "codeur",
  depends_on: [],
  body: "",
  project_id: "mon-projet",
  file_path: "/w/t.md",
  created: "",
  github_issue_url: null,
  pr_number: null,
};

beforeEach(() => vi.restoreAllMocks());

describe("TicketActivity", () => {
  it("n'affiche rien sans ticket sélectionné", () => {
    const { container } = render(
      <TicketActivity projectId="mon-projet" ticket={null} branch={null} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("dit qu'aucun run n'a eu lieu", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [],
      pr_number: null,
      github_remote: null,
    });

    render(<TicketActivity projectId="mon-projet" ticket={ticket} branch={null} />);

    await waitFor(() =>
      expect(screen.getByText(/Aucun run/)).toBeInTheDocument(),
    );
  });

  it("résume les runs du ticket", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [
        {
          id: "r1",
          started_at: "t",
          finished_at: "t",
          rounds: 2,
          approved: true,
          final_status: "done",
          total_cost_usd: 0.42,
        },
      ],
      pr_number: null,
      github_remote: null,
    });

    render(<TicketActivity projectId="mon-projet" ticket={ticket} branch="b" />);

    await waitFor(() => expect(screen.getByText("approuvé")).toBeInTheDocument());
    expect(screen.getByText(/2 tour\(s\)/)).toBeInTheDocument();
  });

  it("explique qu'il faut une branche avant d'ouvrir une PR", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [],
      pr_number: null,
      github_remote: null,
    });

    render(<TicketActivity projectId="mon-projet" ticket={ticket} branch={null} />);

    await waitFor(() =>
      expect(screen.getByText(/pas encore de branche/)).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /Pousser et ouvrir la PR/ }),
    ).toBeDisabled();
  });

  it("pousse et ouvre la PR au clic", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [],
      pr_number: null,
      github_remote: "owner/repo",
    });
    const openPr = vi.spyOn(api.tickets, "openPr").mockResolvedValue({
      pr_number: 7,
      pr_url: "https://github.com/owner/repo/pull/7",
      branch: "ticket-042-slug",
    });

    const user = userEvent.setup();
    render(
      <TicketActivity
        projectId="mon-projet"
        ticket={ticket}
        branch="ticket-042-slug"
      />,
    );

    await user.click(
      await screen.findByRole("button", { name: /Pousser et ouvrir la PR/ }),
    );

    expect(openPr).toHaveBeenCalledWith(
      "mon-projet",
      "ticket-042",
      "ticket-042-slug",
    );
  });

  it("rappelle que le merge reste manuel", async () => {
    // C'est le seul point où un humain tranche, et c'est ce qui rend le reste
    // de l'automatisation acceptable.
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [],
      pr_number: null,
      github_remote: null,
    });

    render(<TicketActivity projectId="mon-projet" ticket={ticket} branch={null} />);

    await waitFor(() =>
      expect(screen.getByText(/merge reste manuel/)).toBeInTheDocument(),
    );
  });
});
