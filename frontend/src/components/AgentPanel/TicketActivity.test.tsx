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

describe("TicketActivity — forge non supportée", () => {
  it("ne propose pas d'ouvrir une PR hors GitHub, et dit où est le dépôt", async () => {
    // Le bouton poussait la branche puis appelait api.github.com : sur GitLab
    // ou Azure il poussait donc sans rien demander avant d'echouer. Sur un
    // depot client, pousser est la decision qui ne se prend pas par megarde.
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-001",
      runs: [],
      pr_number: null,
      github_remote: "https://dev.azure.com/org/p/_git/p",
      pr_supported: false,
      forge: "Azure DevOps",
    });

    render(
      <TicketActivity projectId="p" ticket={ticket} branch="ticket-001-x" />,
    );

    expect(await screen.findByText(/Azure DevOps/)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Pousser et ouvrir la PR/ }),
    ).toBeNull();
  });

  it("propose la PR sur un dépôt GitHub", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-001",
      runs: [],
      pr_number: null,
      github_remote: "https://github.com/moi/repo.git",
      pr_supported: true,
      forge: "GitHub",
    });

    render(
      <TicketActivity projectId="p" ticket={ticket} branch="ticket-001-x" />,
    );

    expect(
      await screen.findByRole("button", { name: /Pousser et ouvrir la PR/ }),
    ).toBeInTheDocument();
  });
});

describe("TicketActivity — raison d'un blocage (ticket-218)", () => {
  it("affiche l'arrêt sous le statut quand un run est bloqué", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [
        {
          id: "r1",
          started_at: "t",
          finished_at: "t",
          rounds: 30,
          approved: false,
          final_status: "blocked",
          total_cost_usd: 0.1,
          arret: "Reached maximum number of turns (30)",
        },
      ],
      pr_number: null,
      github_remote: null,
    });

    render(<TicketActivity projectId="mon-projet" ticket={ticket} branch={null} />);

    await waitFor(() =>
      expect(
        screen.getByText("Reached maximum number of turns (30)"),
      ).toBeInTheDocument(),
    );
  });

  it("n'affiche rien sous le statut quand l'arrêt est absent", async () => {
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
          total_cost_usd: 0.1,
        },
      ],
      pr_number: null,
      github_remote: null,
    });

    render(<TicketActivity projectId="mon-projet" ticket={ticket} branch={null} />);

    await waitFor(() => expect(screen.getByText("approuvé")).toBeInTheDocument());
    expect(screen.queryByTestId("run-arret")).toBeNull();
  });
});

describe("TicketActivity — Revoir le run (ticket-327)", () => {
  it("affiche le bouton sur un run terminé quand onRevoirRun est fourni", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [
        {
          id: "run-xyz",
          started_at: "2026-09-01T10:00:00Z",
          finished_at: "2026-09-01T10:10:00Z",
          rounds: 1,
          approved: true,
          final_status: "done",
          total_cost_usd: 0.1,
        },
      ],
      pr_number: null,
      github_remote: null,
    });

    const handleRevoir = vi.fn();
    render(
      <TicketActivity
        projectId="mon-projet"
        ticket={ticket}
        branch={null}
        onRevoirRun={handleRevoir}
      />,
    );

    const btn = await screen.findByRole("button", { name: /Revoir le run/ });
    expect(btn).toBeInTheDocument();
  });

  it("appelle onRevoirRun avec le runId et le ticketId au clic", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [
        {
          id: "run-xyz",
          started_at: "2026-09-01T10:00:00Z",
          finished_at: "2026-09-01T10:10:00Z",
          rounds: 1,
          approved: true,
          final_status: "done",
          total_cost_usd: 0.1,
        },
      ],
      pr_number: null,
      github_remote: null,
    });

    const handleRevoir = vi.fn();
    const user = userEvent.setup();
    render(
      <TicketActivity
        projectId="mon-projet"
        ticket={ticket}
        branch={null}
        onRevoirRun={handleRevoir}
      />,
    );

    await user.click(await screen.findByRole("button", { name: /Revoir le run/ }));

    expect(handleRevoir).toHaveBeenCalledWith("run-xyz", "ticket-042");
  });

  it("n'affiche pas le bouton quand onRevoirRun est absent", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [
        {
          id: "run-xyz",
          started_at: "2026-09-01T10:00:00Z",
          finished_at: "2026-09-01T10:10:00Z",
          rounds: 1,
          approved: true,
          final_status: "done",
          total_cost_usd: 0.1,
        },
      ],
      pr_number: null,
      github_remote: null,
    });

    render(
      <TicketActivity projectId="mon-projet" ticket={ticket} branch={null} />,
    );

    await waitFor(() => expect(screen.getByText("approuvé")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /Revoir le run/ })).toBeNull();
  });

  it("n'affiche pas le bouton sur un run sans finished_at", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [
        {
          id: "run-live",
          started_at: "2026-09-01T10:00:00Z",
          finished_at: null,
          rounds: null,
          approved: null,
          final_status: null,
          total_cost_usd: 0.0,
        },
      ],
      pr_number: null,
      github_remote: null,
    });

    const handleRevoir = vi.fn();
    render(
      <TicketActivity
        projectId="mon-projet"
        ticket={ticket}
        branch={null}
        onRevoirRun={handleRevoir}
      />,
    );

    await waitFor(() => expect(screen.getByText("en cours")).toBeInTheDocument());
    expect(screen.queryByRole("button", { name: /Revoir le run/ })).toBeNull();
  });
});

describe("TicketActivity — jusqu'où le projet laisse aller (ticket-082)", () => {
  it("dit que le merge reste manuel là où rien n'est déclaré", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [],
      pr_number: 7,
      github_remote: "owner/repo",
      autonomy: "commit",
    });

    render(<TicketActivity projectId="p" ticket={ticket} branch="b" />);

    expect(await screen.findByText(/merge reste manuel/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Merger/ })).toBeNull();
  });

  it("propose le merge là où le projet l'a déclaré", async () => {
    // L'utilisateur veut que Tessera et ses projets perso aillent jusqu'au
    // bout ; ses dépôts clients, non. La différence se déclare, elle ne se
    // devine pas.
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [],
      pr_number: 7,
      github_remote: "owner/repo",
      autonomy: "merge",
    });
    const merge = vi
      .spyOn(api.tickets, "mergePr")
      .mockResolvedValue({ pr_number: 7, merged: true });

    const user = userEvent.setup();
    render(<TicketActivity projectId="p" ticket={ticket} branch="b" />);

    await user.click(await screen.findByRole("button", { name: /Merger/ }));

    expect(merge).toHaveBeenCalledWith("p", "ticket-042");
    expect(screen.queryByText(/merge reste manuel/)).toBeNull();
  });

  it("explique un refus de merge sans faire croire à une panne", async () => {
    vi.spyOn(api.tickets, "activity").mockResolvedValue({
      ticket_id: "ticket-042",
      runs: [],
      pr_number: 7,
      github_remote: "owner/repo",
      autonomy: "merge",
    });
    vi.spyOn(api.tickets, "mergePr").mockRejectedValue(
      new Error("Merge refusé : la CI de la PR doit être verte."),
    );

    const user = userEvent.setup();
    render(<TicketActivity projectId="p" ticket={ticket} branch="b" />);

    await user.click(await screen.findByRole("button", { name: /Merger/ }));

    expect(await screen.findByText(/CI de la PR doit être verte/)).toBeInTheDocument();
  });
});
