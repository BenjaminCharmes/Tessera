import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { boulesDeLaCorbeille } from "./corbeille";

const HORODATAGE = "2026-10-29T09:00:00.000Z";

function ev(
  type: EventType,
  agent: AgentRole | null = null,
  data: Record<string, unknown> = {},
  ticket = "ticket-001",
): OrchestratorEvent {
  return { type, agent, ticket_id: ticket, data, timestamp: HORODATAGE };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const refus = (ticket = "ticket-001") =>
  ev("agent_done", "reviewer", { content: "CHANGES_REQUESTED\n- un test manque", verdict: "CHANGES_REQUESTED" }, ticket);
const accord = () => ev("agent_done", "reviewer", { content: "APPROVED", verdict: "APPROVED" });

describe("boulesDeLaCorbeille", () => {
  it("is empty without any refusal", () => {
    expect(boulesDeLaCorbeille(INITIAL)).toBe(0);
    expect(boulesDeLaCorbeille(rejouer([ev("agent_started", "codeur"), accord()]))).toBe(0);
  });

  it("adds one ball per refusal of the reviewer", () => {
    expect(boulesDeLaCorbeille(rejouer([refus()]))).toBe(1);
    expect(boulesDeLaCorbeille(rejouer([refus(), ev("agent_started", "codeur"), refus()]))).toBe(2);
  });

  it("draws three balls at most", () => {
    const etat = rejouer([refus(), refus(), refus(), refus(), refus()]);

    expect(boulesDeLaCorbeille(etat)).toBe(3);
  });

  it("does not count the refusals of the validator nor of other agents", () => {
    const etat = rejouer([
      ev("validation_done", null, { verdict: "CHANGES_REQUESTED", approved: false }),
      ev("agent_done", "codeur", { content: "CHANGES_REQUESTED" }),
    ]);

    expect(boulesDeLaCorbeille(etat)).toBe(0);
  });

  it("empties when the next ticket resets the ticket events", () => {
    const apres = rejouer([refus(), refus(), ev("queue_progress", null, {}, "ticket-002")]);

    expect(boulesDeLaCorbeille(apres)).toBe(0);
  });

  it("ignores the refusals of another ticket still in the events", () => {
    const etat = rejouer([refus("ticket-001"), ev("agent_started", "codeur", {}, "ticket-002"), refus("ticket-002")]);

    expect(boulesDeLaCorbeille(etat)).toBe(1);
  });
});
