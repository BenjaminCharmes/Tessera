import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RunView from "./index";
import { OuvrirTicketContext } from "../../hooks/useOuvrirTicket";
import type { OuvrirTicket } from "../../hooks/useOuvrirTicket";
import type { UseRunActifResult, PassageAgent } from "../../hooks/streamState";

function flux(over: Partial<UseRunActifResult> = {}) {
  return {
    status: "running",
    ticketId: "ticket-001",
    events: [],
    entries: [],
    currentAgent: null,
    currentRound: 0,
    currentTokens: "",
    lastResult: null,
    errorMessage: null,
    quota: null,
    pendingQuestion: null,
    queue: null,
    connect: () => {},
    connectQueue: () => {},
    disconnect: () => {},
    clear: () => {},
    answer: () => {},
    interject: () => {},
    stop: () => {},
    ...over,
  } as UseRunActifResult;
}

function passage(over: Partial<PassageAgent>): PassageAgent {
  return {
    genre: "agent",
    id: "codeur-0",
    agent: "codeur",
    round: 1,
    tokens: "",
    content: "",
    isDone: false,
    ...over,
  };
}

describe("RunView", () => {
  it("dit que le run démarre tant qu'aucun agent n'a parlé", () => {
    render(<RunView stream={flux()} />);

    expect(screen.getByText(/Le run démarre/i)).toBeInTheDocument();
  });

  it("n'affiche que les agents qui ont démarré", () => {
    // Six blocs vides diraient qu'il ne se passe rien.
    render(
      <RunView
        stream={flux({
          entries: [passage({ agent: "codeur", id: "codeur-0" })],
        })}
      />,
    );

    expect(screen.getByText("CODEUR")).toBeInTheDocument();
    expect(screen.queryByText("REVIEWER")).toBeNull();
  });

  it("montre le tour et l'agent qui parle", () => {
    render(<RunView stream={flux({ currentRound: 2, currentAgent: "reviewer" })} />);

    expect(screen.getByText("Tour 2")).toBeInTheDocument();
    expect(screen.getByText("REVIEWER")).toBeInTheDocument();
  });

  it("montre l'avancement d'une file", () => {
    render(<RunView stream={flux({ queue: { index: 2, total: 3 } })} />);

    expect(screen.getByText(/File : 2\/3/)).toBeInTheDocument();
  });
});

describe("RunView — fil chronologique (ticket-222)", () => {
  it("replie une entrée terminée, affiche son résumé, et la déplie au clic", async () => {
    // Trois entrées : codeur tour 1 (terminé), reviewer tour 1 (terminé),
    // codeur tour 2 (actif). Les deux premières doivent être repliées.
    const entries: PassageAgent[] = [
      passage({ id: "codeur-0", agent: "codeur", round: 1, isDone: true, content: "Implémentation faite." }),
      passage({ id: "reviewer-1", agent: "reviewer", round: 1, isDone: true, content: "CHANGES_REQUESTED\nAjoute des tests." }),
      passage({ id: "codeur-2", agent: "codeur", round: 2, isDone: false, tokens: "En cours…" }),
    ];

    render(<RunView stream={flux({ entries })} />);

    // Le résumé CHANGES_REQUESTED est visible dans l'en-tête replié du reviewer.
    expect(screen.getByText("CHANGES_REQUESTED")).toBeInTheDocument();

    // L'entrée est repliée : le corps (VerdictBanner) n'est pas dans le DOM.
    expect(screen.queryByText(/Ajoute des tests/)).toBeNull();

    // Cliquer sur l'en-tête du reviewer pour le déplier.
    const reviewerHeader = screen.getByRole("button", { name: /REVIEWER/i });
    await userEvent.click(reviewerHeader);

    // VerdictBanner.parseVerdict filtre "CHANGES_REQUESTED" et met
    // "Ajoute des tests." dans summary — visible dès l'expansion, sans clic
    // supplémentaire dans VerdictBanner.
    expect(screen.getByText(/Ajoute des tests/)).toBeInTheDocument();
  });

  it("affiche deux entrées pour un run à un seul tour sans libellé de tour par entrée", () => {
    const entries: PassageAgent[] = [
      passage({ id: "codeur-0", agent: "codeur", round: 1, isDone: true, content: "Tout est fait." }),
      passage({ id: "reviewer-1", agent: "reviewer", round: 1, isDone: true, content: "APPROVED" }),
    ];

    render(<RunView stream={flux({ entries, currentRound: 0 })} />);

    // Les deux entrées sont affichées.
    const blocs = screen.getAllByTestId("entree-pipeline");
    expect(blocs).toHaveLength(2);

    // Aucun libellé "Tour 1 — CODEUR" ni "Tour 1 — REVIEWER" dans les en-têtes.
    expect(screen.queryByText(/Tour 1\s*[—–]\s*CODEUR/i)).toBeNull();
    expect(screen.queryByText(/Tour 1\s*[—–]\s*REVIEWER/i)).toBeNull();
  });
});

describe("RunView — le numéro du ticket ouvre le ticket (ticket-460)", () => {
  function rendreAvecAction(projectId: string | null) {
    const ouvrir = vi.fn<OuvrirTicket>().mockResolvedValue("ok");
    render(
      <OuvrirTicketContext.Provider value={ouvrir}>
        <RunView stream={flux()} projectId={projectId} />
      </OuvrirTicketContext.Provider>,
    );
    return ouvrir;
  }

  it("opens the ticket of the run from the header", async () => {
    const ouvrir = rendreAvecAction("p1");

    await userEvent.click(screen.getByRole("button", { name: "ticket-001" }));

    expect(ouvrir).toHaveBeenCalledWith("p1", "ticket-001");
  });

  it("is activated by Enter", async () => {
    const ouvrir = rendreAvecAction("p1");

    screen.getByRole("button", { name: "ticket-001" }).focus();
    await userEvent.keyboard("{Enter}");

    expect(ouvrir).toHaveBeenCalledWith("p1", "ticket-001");
  });

  it("keeps the id as plain text without a project", () => {
    rendreAvecAction(null);

    expect(screen.queryByRole("button", { name: "ticket-001" })).toBeNull();
    expect(screen.getByText("ticket-001")).toBeInTheDocument();
  });
});
