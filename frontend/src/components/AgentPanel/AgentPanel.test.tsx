import { describe, it, expect, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import RoundBadge from "./RoundBadge";
import PipelineSummary from "./PipelineSummary";
import TokenStream from "./TokenStream";
import AgentBlock from "./AgentBlock";
import AgentPanel from "./index";
import type { PipelineResult } from "../../types/api";
import type { UseRunActifResult, EntreeFil } from "../../hooks/streamState";

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = () => {};
});

const APPROVED: PipelineResult = {
  ticket_id: "ticket-001",
  final_status: "done",
  rounds: 2,
  approved: true,
};

const REJECTED: PipelineResult = {
  ticket_id: "ticket-002",
  final_status: "todo",
  rounds: 3,
  approved: false,
};

describe("RoundBadge", () => {
  it("renders current round and default max", () => {
    render(<RoundBadge current={1} />);
    expect(screen.getByText("Tour 1 / 3")).toBeTruthy();
  });

  it("renders custom max", () => {
    render(<RoundBadge current={2} max={5} />);
    expect(screen.getByText("Tour 2 / 5")).toBeTruthy();
  });
});

describe("PipelineSummary", () => {
  it("shows approved message when approved", () => {
    render(<PipelineSummary result={APPROVED} />);
    expect(screen.getByText(/Pipeline terminé/)).toBeTruthy();
    expect(screen.getByText("ticket-001")).toBeTruthy();
    expect(screen.getByText("done")).toBeTruthy();
  });

  it("shows rejected message when not approved", () => {
    render(<PipelineSummary result={REJECTED} />);
    expect(screen.getByText(/Non approuvé/)).toBeTruthy();
  });

  it("shows duration when provided", () => {
    render(<PipelineSummary result={APPROVED} durationMs={5000} />);
    expect(screen.getByText("5s")).toBeTruthy();
  });

  it("hides duration when not provided", () => {
    render(<PipelineSummary result={APPROVED} />);
    expect(screen.queryByText(/Durée/)).toBeNull();
  });

  it("affiche livraison en cours entre pipeline_done et run_closed (ticket-267)", () => {
    // Entre pipeline_done et run_closed, la livraison tourne encore.
    render(<PipelineSummary result={APPROVED} runClosed={false} />);
    expect(screen.getByText(/livraison en cours/)).toBeTruthy();
    expect(screen.queryByText(/Pipeline terminé/)).toBeNull();
  });

  it("affiche Pipeline terminé apres run_closed (ticket-267)", () => {
    render(<PipelineSummary result={APPROVED} runClosed={true} />);
    expect(screen.getByText(/Pipeline terminé/)).toBeTruthy();
    expect(screen.queryByText(/livraison en cours/)).toBeNull();
  });
});

describe("TokenStream", () => {
  it("renders tokens", () => {
    render(<TokenStream tokens="hello world" isActive={false} />);
    expect(screen.getByText("hello world")).toBeTruthy();
  });

  it("shows cursor when active", () => {
    // Le curseur est un bloc dessiné depuis ticket-067 : il n'a plus de
    // contenu textuel, donc on l'observe par sa classe d'animation.
    const { container } = render(<TokenStream tokens="typing…" isActive={true} />);
    expect(container.querySelector(".animate-pulse")).toBeTruthy();
  });

  it("hides cursor when inactive", () => {
    render(<TokenStream tokens="done" isActive={false} />);
    expect(screen.queryByText("█")).toBeNull();
  });
});

describe("AgentBlock", () => {
  it("renders codeur label", () => {
    render(
      <AgentBlock
        agent="codeur"
        tokens="some code"
        isActive={false}
        isDone={true}
      />,
    );
    expect(screen.getByText(/CODEUR/)).toBeTruthy();
  });

  it("marque un agent termine, en vert plutot qu en gris", () => {
    render(
      <AgentBlock agent="codeur" tokens="" isActive={false} isDone={true} />,
    );
    expect(screen.getByText("terminé")).toBeTruthy();
  });

  it("montre un texte d attente quand l agent n a rien produit", () => {
    render(
      <AgentBlock agent="codeur" tokens="" isActive={true} isDone={false} />,
    );
    expect(screen.getByText(/Génération/i)).toBeTruthy();
  });

  it("renders reviewer label and verdict", () => {
    render(
      <AgentBlock
        agent="reviewer"
        tokens=""
        isActive={false}
        isDone={true}
        reviewContent="APPROVED: looks good"
      />,
    );
    expect(screen.getByText(/REVIEWER/)).toBeTruthy();
    expect(screen.getByText(/APPROVED/)).toBeTruthy();
  });

  it("uses agent name as fallback label for unknown roles", () => {
    render(
      <AgentBlock
        agent={"testeur" as "codeur"}
        tokens=""
        isActive={false}
        isDone={false}
      />,
    );
    expect(screen.getByText("TESTEUR")).toBeTruthy();
  });
});

// ---------------------------------------------------------------------------
// AgentPanel — fil chronologique multi-tours (ticket-257)
// ---------------------------------------------------------------------------

function streamMock(over: Partial<UseRunActifResult> = {}): UseRunActifResult {
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
    etape: null,
    quota: null,
    pendingQuestion: null,
    questionExpireA: null,
    queue: null,
    branch: null,
    coutUsd: 0,
    appels: 0,
    outils: 0,
    maxRounds: null,
    runClosed: false,
    connect: () => {},
    connectQueue: () => {},
    connectAutonome: () => {},
    disconnect: () => {},
    clear: () => {},
    answer: () => {},
    interject: () => {},
    stop: () => {},
    ...over,
  } as UseRunActifResult;
}

describe("AgentPanel — fil multi-tours (ticket-257)", () => {
  it("montre le passage du codeur au tour 1 apres le tour 2", () => {
    // Trois entrées : codeur t1 (done), reviewer t1 (done), codeur t2 (actif).
    // Le codeur tour 1 doit rester dans le DOM même après le tour 2.
    const entries: EntreeFil[] = [
      {
        genre: "agent",
        id: "codeur-0",
        agent: "codeur",
        round: 1,
        tokens: "",
        content: "Implémentation tour 1.",
        isDone: true,
      },
      {
        genre: "agent",
        id: "reviewer-1",
        agent: "reviewer",
        round: 1,
        tokens: "",
        content: "CHANGES_REQUESTED\nAjoute des tests.",
        isDone: true,
      },
      {
        genre: "agent",
        id: "codeur-2",
        agent: "codeur",
        round: 2,
        tokens: "En cours...",
        content: "",
        isDone: false,
      },
    ];

    render(
      <AgentPanel
        project={null}
        stream={streamMock({ entries, currentRound: 2 })}
      />,
    );

    // Les trois entrées sont affichées : codeur t1, reviewer t1, codeur t2.
    const blocs = screen.getAllByTestId("entree-pipeline");
    expect(blocs.length).toBe(3);

    // Le libellé CODEUR apparaît deux fois (tour 1 et tour 2).
    const coderHeaders = screen.getAllByText("CODEUR");
    expect(coderHeaders.length).toBeGreaterThanOrEqual(2);
  });
});
