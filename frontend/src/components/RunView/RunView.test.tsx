import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import RunView from "./index";
import type { OrchestratorEvent } from "../../types/api";
import type { UseRunActifResult } from "../../hooks/streamState";

function evenement(
  type: OrchestratorEvent["type"],
  agent: OrchestratorEvent["agent"],
  data: Record<string, unknown> = {},
): OrchestratorEvent {
  return {
    type,
    agent,
    ticket_id: "ticket-001",
    data,
    timestamp: "2026-09-17T10:00:00Z",
  };
}

function flux(over: Partial<UseRunActifResult> = {}) {
  return {
    status: "running",
    ticketId: "ticket-001",
    events: [],
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

describe("RunView", () => {
  it("dit que le run démarre tant qu'aucun agent n'a parlé", () => {
    render(<RunView stream={flux()} />);

    expect(screen.getByText(/Le run démarre/i)).toBeInTheDocument();
  });

  it("n'affiche que les agents qui ont démarré", () => {
    // Six blocs vides diraient qu'il ne se passe rien.
    render(
      <RunView
        stream={flux({ events: [evenement("agent_started", "codeur")] })}
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
