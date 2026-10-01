import { describe, it, expect } from "vitest";
import { applyEvent, INITIAL } from "./streamState";
import type { OrchestratorEvent } from "../types/api";
import type { EntreeSecurite, EntreeValidateur } from "./streamState";

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

describe("applyEvent — fil chronologique des passages (ticket-222)", () => {
  it("garde le verdict du reviewer au tour 1 après agent_started du codeur au tour 2", () => {
    let s = INITIAL;
    // Tour 1 : codeur puis reviewer
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "Implémentation terminée." } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "CHANGES_REQUESTED\nAjoute des tests." } }));
    // Tour 2 : le codeur reprend
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 2 } }));

    // Le verdict du reviewer du tour 1 doit rester dans les entrées.
    const reviewerEntry = s.entries.find((e) => e.genre === "agent" && e.agent === "reviewer" && e.isDone);
    expect(reviewerEntry).toBeDefined();
    expect(reviewerEntry?.genre === "agent" ? reviewerEntry.content : "").toContain("CHANGES_REQUESTED");
  });

  it("un run à deux tours produit quatre entrées dans l'ordre codeur, reviewer, codeur, reviewer", () => {
    let s = INITIAL;
    // Tour 1
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "v1" } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "CHANGES_REQUESTED" } }));
    // Tour 2
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 2 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "v2" } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: { round: 2 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "APPROVED" } }));

    expect(s.entries).toHaveLength(4);
    expect(s.entries.map((e) => (e.genre === "agent" ? e.agent : e.genre))).toEqual([
      "codeur", "reviewer", "codeur", "reviewer",
    ]);
  });
});

describe("applyEvent — ticket_id depuis ev.ticket_id et run_closed (ticket-267)", () => {
  it("lit le ticket_id au premier niveau de l'evenement, pas seulement dans data", () => {
    // Le backend émet ticket_id en champ racine de l'événement ; data["ticket_id"]
    // est un doublon de confort absent de certains backends.
    const s = applyEvent(
      INITIAL,
      ev({
        type: "pipeline_done",
        ticket_id: "ticket-267",
        data: { approved: true, rounds: 1, final_status: "done" },
      }),
    );
    expect(s.lastResult?.ticket_id).toBe("ticket-267");
  });

  it("marque runClosed a true sur run_closed", () => {
    const s = applyEvent(INITIAL, ev({ type: "run_closed" }));
    expect(s.runClosed).toBe(true);
  });

  it("runClosed reste false apres pipeline_done", () => {
    // Entre pipeline_done et run_closed, la livraison tourne encore.
    const s = applyEvent(
      INITIAL,
      ev({
        type: "pipeline_done",
        ticket_id: "ticket-267",
        data: { approved: true, rounds: 1, final_status: "done" },
      }),
    );
    expect(s.runClosed).toBe(false);
  });
});

describe("applyEvent — entrées securite et validateur dans le fil (ticket-257)", () => {
  it("security_audit_done ajoute une EntreeSecurite avec le verdict", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "ok" } }));
    s = applyEvent(s, ev({
      type: "security_audit_done",
      agent: null,
      data: { verdict: "APPROVED", summary: "Aucune faille détectée.", issues_count: 0, reason: "" },
    }));

    expect(s.entries).toHaveLength(2);
    const auditEntry = s.entries[1] as EntreeSecurite;
    expect(auditEntry.genre).toBe("securite");
    expect(auditEntry.verdict).toBe("APPROVED");
    expect(auditEntry.summary).toBe("Aucune faille détectée.");
    expect(auditEntry.isDone).toBe(true);
  });

  it("validation_done ajoute une EntreeValidateur avec ses critères", () => {
    let s = INITIAL;
    s = applyEvent(s, ev({ type: "agent_started", agent: "codeur", data: { round: 1 } }));
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "ok" } }));
    s = applyEvent(s, ev({
      type: "validation_done",
      agent: null,
      data: {
        verdict: "CHANGES_REQUESTED",
        feedback: "Deux critères échoués.",
        criteria: [
          { criterion: "Tests unitaires", passed: false, note: "Aucun test pour foo()." },
          { criterion: "Typage", passed: true, note: "" },
        ],
      },
    }));

    expect(s.entries).toHaveLength(2);
    const validEntry = s.entries[1] as EntreeValidateur;
    expect(validEntry.genre).toBe("validateur");
    expect(validEntry.verdict).toBe("CHANGES_REQUESTED");
    expect(validEntry.feedback).toBe("Deux critères échoués.");
    expect(validEntry.criteria).toHaveLength(2);
    expect(validEntry.criteria[0]).toEqual({
      criterion: "Tests unitaires",
      passed: false,
      note: "Aucun test pour foo().",
    });
    expect(validEntry.isDone).toBe(true);
  });
});

describe("applyEvent — coût en direct (ticket-197)", () => {
  it("cumule le coût et compte les appels, et remet les outils à zéro par agent", () => {
    let s = applyEvent(INITIAL, ev({ type: "agent_started", agent: "codeur", data: {} }));
    s = applyEvent(s, ev({ type: "agent_tool_use", agent: "codeur", data: { tool: "Read" } }));
    s = applyEvent(s, ev({ type: "agent_tool_use", agent: "codeur", data: { tool: "Edit" } }));
    expect(s.outils).toBe(2);
    s = applyEvent(s, ev({ type: "agent_done", agent: "codeur", data: { content: "", cost_usd: 0.4 } }));
    s = applyEvent(s, ev({ type: "agent_started", agent: "reviewer", data: {} }));
    expect(s.outils).toBe(0);
    s = applyEvent(s, ev({ type: "agent_done", agent: "reviewer", data: { content: "APPROVED", cost_usd: 0.2 } }));
    expect(s.coutUsd).toBeCloseTo(0.6);
    expect(s.appels).toBe(2);
  });
});
