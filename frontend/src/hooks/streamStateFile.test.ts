import { describe, it, expect } from "vitest";
import { applyEvent, INITIAL } from "./streamState";
import type { OrchestratorEvent } from "../types/api";

function ev(over: Partial<OrchestratorEvent>): OrchestratorEvent {
  return {
    type: "agent_started",
    agent: "codeur",
    ticket_id: "ticket-012",
    data: {},
    timestamp: new Date().toISOString(),
    run_id: "r1",
    project_id: "demineur",
    ...over,
  } as OrchestratorEvent;
}

/** L'état d'un run de file arrivé au bout du ticket-012. */
function apresLePremierTicket() {
  let s = INITIAL;
  s = applyEvent(s, ev({ type: "queue_progress", ticket_id: "ticket-012", data: { index: 1, total: 3 } }));
  s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
  s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer" }));
  s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "APPROVED" } }));
  s = applyEvent(s, ev({ type: "agent_question", data: { question: "on casse l'API ?" } }));
  s = applyEvent(s, ev({ type: "quota_updated", data: { utilization: 0.4 } }));
  return s;
}

describe("applyEvent — un ticket de file n'hérite pas du précédent (ticket-180)", () => {
  it("oublie les événements du ticket précédent", () => {
    // Le bloc reviewer de ticket-012 restait affiché sous le codeur de
    // ticket-013, verdict APPROVED compris.
    const avant = apresLePremierTicket();

    const apres = applyEvent(
      avant,
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(
      apres.events.some((e) => e.type === "agent_done" && e.agent === "reviewer"),
    ).toBe(false);
  });

  it("oublie l'agent courant et le tour du ticket précédent", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.currentAgent).toBeNull();
    expect(apres.currentRound).toBe(0);
  });

  it("oublie une question restée en attente", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.pendingQuestion).toBeNull();
  });

  it("garde ce qui appartient au run : avancement et quota", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.queue).toEqual({ index: 2, total: 3 });
    expect(apres.quota).not.toBeNull();
  });

  it("prend le ticket annoncé et reste en cours", () => {
    const apres = applyEvent(
      apresLePremierTicket(),
      ev({ type: "queue_progress", ticket_id: "ticket-013", data: { index: 2, total: 3 } }),
    );

    expect(apres.ticketId).toBe("ticket-013");
    expect(apres.status).toBe("running");
  });
});
