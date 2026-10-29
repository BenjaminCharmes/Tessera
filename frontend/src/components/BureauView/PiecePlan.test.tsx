import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import { api } from "../../lib/api";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import Piece from "./Piece";
import { DERNIER, T0, nomme } from "./etatsDeTest";

beforeEach(() => {
  vi.stubGlobal("innerWidth", 2400);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function ev(type: EventType, agent: AgentRole, data: Record<string, unknown> = {}): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: DERNIER };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const PLAN = { round: 0, phase: "plan" };

describe("Piece plan and architect", () => {
  it("names the coder post after the architect once it starts", () => {
    const etat = rejouer([ev("agent_started", "architect")]);

    render(<Piece projet="ide-core" etat={etat} maintenant={T0} />);

    expect(screen.getByRole("button", { name: nomme("Architecte, travaille", "architect") })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /, codeur, / })).toBeNull();
  });

  it("stands the agent at the whiteboard during the plan, then back at the post", () => {
    const pendant = rejouer([ev("agent_started", "codeur", PLAN)]);
    const { container, rerender } = render(<Piece projet="ide-core" etat={pendant} maintenant={T0} />);

    const agent = container.querySelector('[data-agent="codeur"]');
    expect(agent?.getAttribute("data-activite")).toBe("plan");
    expect(screen.getByRole("img", { name: nomme("Codeur, prépare le plan", "codeur") })).toBeInTheDocument();

    const apres = rejouer([ev("agent_started", "codeur", PLAN), ev("agent_done", "codeur", PLAN)]);
    rerender(<Piece projet="ide-core" etat={apres} maintenant={T0} />);

    expect(container.querySelector('[data-agent="codeur"]')).toBeNull();
    expect(screen.getByRole("button", { name: nomme("Codeur, attend son tour", "codeur") })).toBeInTheDocument();
  });
});
