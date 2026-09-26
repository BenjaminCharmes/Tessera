import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import TicketList from "./TicketList";
import type { Project, Ticket, TicketStatus } from "../../types/api";

vi.mock("../../lib/api");

const PROJET: Project = {
  id: "ide-core",
  name: "ide-core",
  path: "/ws/ide-core",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

const VIDE = {
  todo: [], "in-progress": [], "in-review": [], done: [], blocked: [],
  cancelled: [],
} as Record<TicketStatus, Ticket[]>;

function props(loading: boolean) {
  return {
    project: PROJET,
    byStatus: VIDE,
    loading,
    error: null,
    activeTicket: null,
    running: new Set<string>(),
    showKanban: false,
    onSelectTicket: () => {},
    onRunPipeline: () => {},
    onToggleKanban: () => {},
  };
}

describe("TicketList", () => {
  it("garde la modale montee quand les tickets se rechargent", async () => {
    // Panne vecue : `TicketList` retournait tot sur `loading`, ce qui
    // demontait tout le sous-arbre — modale comprise. Les brouillons du
    // planificateur, resultat d'un appel facture, disparaissaient au premier
    // rafraichissement des tickets, quelques secondes apres s'etre affiches.
    const { rerender } = render(<TicketList {...props(false)} />);

    await userEvent.click(
      screen.getByRole("button", { name: /planifier une évolution/i }),
    );
    expect(screen.getByRole("dialog")).toBeInTheDocument();

    rerender(<TicketList {...props(true)} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("montre le squelette pendant le chargement", () => {
    render(<TicketList {...props(true)} />);

    expect(screen.getByRole("button", { name: /planifier une évolution/i }))
      .toBeInTheDocument();
  });
});

describe("TicketList — filtres (ticket-195)", () => {
  it("dit combien les filtres cachent", () => {
    // Une liste vide sans explication se lit comme un projet sans tickets.
    render(
      <TicketList
        {...props(false)}
        filtres={{ texte: "introuvable", type: "", priorite: "", agent: "", tri: "numero" }}
        onChangeFiltres={() => {}}
        totalTickets={12}
      />,
    );
    expect(screen.getByText("0 sur 12")).toBeInTheDocument();
  });

  it("n'affiche pas de barre sans filtres", () => {
    render(<TicketList {...props(false)} />);
    expect(screen.queryByLabelText("Chercher un ticket")).not.toBeInTheDocument();
  });

  it("propage une recherche", async () => {
    const onChangeFiltres = vi.fn();
    render(
      <TicketList
        {...props(false)}
        filtres={{ texte: "", type: "", priorite: "", agent: "", tri: "numero" }}
        onChangeFiltres={onChangeFiltres}
        totalTickets={0}
      />,
    );
    await userEvent.type(screen.getByLabelText("Chercher un ticket"), "c");
    expect(onChangeFiltres).toHaveBeenCalledWith(
      expect.objectContaining({ texte: "c" }),
    );
  });
});
