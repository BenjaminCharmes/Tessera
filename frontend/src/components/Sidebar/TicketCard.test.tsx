import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import TicketCard from "./TicketCard";
import type { Ticket } from "../../types/api";
import * as apiModule from "../../lib/api";

const base: Ticket = {
  id: "ticket-001",
  title: "Add authentication module",
  type: "feat",
  status: "todo",
  priority: "high",
  agent: "codeur",
  depends_on: [],
  created: "2026-06-20",
  github_issue_url: null,
  pr_number: null,
  body: "Implement OAuth2 login flow",
  project_id: "ide-core",
  file_path: "/projects/ide-core/tickets/todo/ticket-001.md",
};

describe("TicketCard", () => {
  it("renders ticket id and title", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("ticket-001")).toBeInTheDocument();
    expect(screen.getByText("Add authentication module")).toBeInTheDocument();
  });

  it("renders status and priority badges", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("todo")).toBeInTheDocument();
    expect(screen.getByText("high")).toBeInTheDocument();
  });

  it("calls onSelect when card is clicked", () => {
    const onSelect = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={onSelect}
        onRun={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByText("Add authentication module"));
    expect(onSelect).toHaveBeenCalledWith(base);
  });

  it("s'ouvre à la touche Entrée et à Espace (ticket-123)", () => {
    // La carte était un `div onClick` : invisible au clavier.
    const onSelect = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={onSelect}
        onRun={vi.fn()}
      />,
    );
    const carte = screen.getByRole("button", { name: /Add authentication module/ });
    expect(carte).toHaveAttribute("tabindex", "0");
    fireEvent.keyDown(carte, { key: "Enter" });
    fireEvent.keyDown(carte, { key: " " });
    expect(onSelect).toHaveBeenCalledTimes(2);
  });

  it("une touche dans un bouton interne n'ouvre pas la carte", () => {
    const onSelect = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={onSelect}
        onRun={vi.fn()}
      />,
    );
    fireEvent.keyDown(screen.getByRole("button", { name: "Lancer le pipeline" }), {
      key: "Enter",
    });
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("compte les tours seulement quand le maximum est connu (ticket-123)", () => {
    const { rerender } = render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning
        runningRound={2}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("tour 2")).toBeInTheDocument();
    rerender(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning
        runningRound={2}
        maxRounds={3}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("tour 2/3")).toBeInTheDocument();
  });

  it("calls onRun with ticket id when run button clicked", () => {
    const onRun = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={onRun}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Lancer le pipeline" }));
    expect(onRun).toHaveBeenCalledWith("ticket-001");
  });

  it("run click does not bubble to onSelect", () => {
    const onSelect = vi.fn();
    const onRun = vi.fn();
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={onSelect}
        onRun={onRun}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Lancer le pipeline" }));
    expect(onSelect).not.toHaveBeenCalled();
  });

  it("shows animate-pulse indicator when running", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={true}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    const pulse = document.querySelector(".animate-pulse")!;
    expect(pulse).toHaveClass("animate-pulse");
  });

  it("run button is disabled when running", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={true}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByRole("button", { name: "Lancer le pipeline" })).toBeDisabled();
  });

  it("no run button for done tickets", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Run pipeline")).not.toBeInTheDocument();
  });

  it("no run button for cancelled tickets", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "cancelled" }}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Run pipeline")).not.toBeInTheDocument();
  });

  it("applies active styling when isActive", () => {
    const { container } = render(
      <TicketCard
        ticket={base}
        isActive={true}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(container.firstChild).toHaveClass("bg-zinc-700");
  });

  // ------------------------------------------------------------------
  // PR button — retiré (ticket-205)
  // ------------------------------------------------------------------

  it("never offers to open a PR from the card", () => {
    // Le cas où le bouton apparaissait : terminé, remote, sans numéro. La
    // livraison note désormais sa PR ; ouvrir une PR à la main passe par le
    // panneau d'activité, qui pousse la branche avant.
    render(
      <TicketCard
        ticket={{ ...base, status: "done" }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.queryByTitle("Ouvrir une PR")).not.toBeInTheDocument();
    expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
  });

  // ------------------------------------------------------------------
  // PR badge
  // ------------------------------------------------------------------

  it("shows PR number badge when pr_number set", () => {
    vi.spyOn(apiModule.api.github, "getPrStatus").mockResolvedValue({
      state: "open",
      ci_status: "none",
      pr_url: "https://github.com/owner/repo/pull/7",
      pr_number: 7,
    });

    render(
      <TicketCard
        ticket={{ ...base, pr_number: 7 }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    expect(screen.getByText("PR #7")).toBeInTheDocument();
  });

  it("shows CI status badge after polling resolves", async () => {
    vi.spyOn(apiModule.api.github, "getPrStatus").mockResolvedValue({
      state: "open",
      ci_status: "passing",
      pr_url: "https://github.com/owner/repo/pull/7",
      pr_number: 7,
    });

    render(
      <TicketCard
        ticket={{ ...base, pr_number: 7 }}
        isActive={false}
        isRunning={false}
        githubRemote="owner/repo"
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );

    await waitFor(() => {
      expect(screen.getByText("CI verte")).toBeInTheDocument();
    });
  });

  it("stops polling a PR the server reports as not found", async () => {
    // ticket-217 : un pr_number hérité d'un autre dépôt renvoie 404. La carte
    // réessayait toutes les 30 s, sur 106 cartes à la fois.
    vi.useFakeTimers();
    try {
      const spy = vi
        .spyOn(apiModule.api.github, "getPrStatus")
        .mockRejectedValue(new Error("API 404: PR #132 introuvable"));

      render(
        <TicketCard
          ticket={{ ...base, pr_number: 132 }}
          isActive={false}
          isRunning={false}
          githubRemote="owner/repo"
          onSelect={vi.fn()}
          onRun={vi.fn()}
        />,
      );
      await vi.advanceTimersByTimeAsync(0);
      expect(spy).toHaveBeenCalledTimes(1);

      await vi.advanceTimersByTimeAsync(5 * 60_000);
      expect(spy).toHaveBeenCalledTimes(1);
    } finally {
      vi.useRealTimers();
    }
  });

  it("keeps polling after a transient server error", async () => {
    vi.useFakeTimers();
    try {
      const spy = vi
        .spyOn(apiModule.api.github, "getPrStatus")
        .mockRejectedValue(new Error("API 502: Bad Gateway"));

      render(
        <TicketCard
          ticket={{ ...base, pr_number: 7 }}
          isActive={false}
          isRunning={false}
          githubRemote="owner/repo"
          onSelect={vi.fn()}
          onRun={vi.fn()}
        />,
      );
      await vi.advanceTimersByTimeAsync(0);
      await vi.advanceTimersByTimeAsync(30_000);
      expect(spy).toHaveBeenCalledTimes(2);
    } finally {
      vi.useRealTimers();
    }
  });

  it("n'offre pas la file sur un ticket deja termine", () => {
    // ticket-115 : le bouton « Lancer » etait bien cache sur un `done`, pas
    // celui de la file — et run_queue ne regardait pas le statut. Le ticket
    // etait donc reellement repris : nouvelle branche, nouveaux appels
    // d'agents, quota depense, pour refaire un travail livre.
    for (const status of ["done", "cancelled"] as const) {
      const { unmount } = render(
        <TicketCard
          ticket={{ ...base, status }}
          isActive={false}
          isRunning={false}
          onSelect={vi.fn()}
          onRun={vi.fn()}
          onToggleQueue={vi.fn()}
        />,
      );

      expect(
        screen.queryByRole("button", { name: /file/i }),
      ).not.toBeInTheDocument();
      expect(
        screen.queryByRole("button", { name: "Lancer le pipeline" }),
      ).not.toBeInTheDocument();
      unmount();
    }
  });

  it("offre la file sur un ticket en cours", () => {
    render(
      <TicketCard
        ticket={base}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
        onToggleQueue={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Ajouter à la file" }),
    ).toBeInTheDocument();
  });
});

describe("TicketCard — infobulle d'arrêt (ticket-218)", () => {
  it("une carte blocked porte l'arrêt dans son attribut title", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "blocked" }}
        arret="Reached maximum number of turns (30)"
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    const badge = screen.getByText("blocked");
    expect(badge).toHaveAttribute("title", "Reached maximum number of turns (30)");
  });

  it("une carte blocked sans arrêt n'a pas de title", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "blocked" }}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    const badge = screen.getByText("blocked");
    expect(badge).not.toHaveAttribute("title");
  });

  it("une carte non-blocked ignore l'arrêt", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "todo" }}
        arret="quelque chose"
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
      />,
    );
    const badge = screen.getByText("todo");
    expect(badge).not.toHaveAttribute("title");
  });
});

describe("TicketCard — statut à la main (ticket-194)", () => {
  it("n'offre aucun menu sans onChangeStatus", () => {
    render(
      <TicketCard ticket={base} isActive={false} isRunning={false} onSelect={vi.fn()} onRun={vi.fn()} />,
    );
    expect(screen.queryByLabelText("Statut de ticket-001")).not.toBeInTheDocument();
  });

  it("ne propose ni in-progress ni in-review", () => {
    // Ces statuts sont tenus par le pipeline : un ticket in-progress sans run
    // se lirait comme un run fantome (ticket-177).
    render(
      <TicketCard
        ticket={{ ...base, status: "blocked" }}
        isActive={false}
        isRunning={false}
        onSelect={vi.fn()}
        onRun={vi.fn()}
        onChangeStatus={vi.fn()}
      />,
    );
    const options = Array.from(
      (screen.getByLabelText("Statut de ticket-001") as HTMLSelectElement).options,
    ).map((o) => o.value);
    expect(options).toEqual(["blocked", "todo", "done", "cancelled"]);
  });

  it("n'a pas de menu pendant un run", () => {
    render(
      <TicketCard
        ticket={{ ...base, status: "todo" }}
        isActive={false}
        isRunning={true}
        onSelect={vi.fn()}
        onRun={vi.fn()}
        onChangeStatus={vi.fn()}
      />,
    );
    expect(screen.queryByLabelText("Statut de ticket-001")).not.toBeInTheDocument();
  });

  it("appelle onChangeStatus avec le statut choisi, sans selectionner la carte", () => {
    const onChangeStatus = vi.fn();
    const onSelect = vi.fn();
    render(
      <TicketCard
        ticket={{ ...base, status: "blocked" }}
        isActive={false}
        isRunning={false}
        onSelect={onSelect}
        onRun={vi.fn()}
        onChangeStatus={onChangeStatus}
      />,
    );
    fireEvent.change(screen.getByLabelText("Statut de ticket-001"), {
      target: { value: "todo" },
    });
    expect(onChangeStatus).toHaveBeenCalledWith("ticket-001", "todo");
    expect(onSelect).not.toHaveBeenCalled();
  });
});
