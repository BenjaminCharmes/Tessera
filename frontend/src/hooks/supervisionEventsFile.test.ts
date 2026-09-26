import { describe, it, expect } from "vitest";
import { majDesRuns } from "./supervisionEvents";
import type { OrchestratorEvent, RunActif } from "../types/api";

function ev(over: Partial<OrchestratorEvent>): OrchestratorEvent {
  return {
    type: "queue_progress",
    agent: null,
    ticket_id: "ticket-016",
    data: {},
    timestamp: new Date().toISOString(),
    run_id: "r1",
    project_id: "demineur",
    ...over,
  } as OrchestratorEvent;
}

function run(over: Partial<RunActif> = {}): RunActif {
  return {
    run_id: "r1",
    project_id: "demineur",
    mode: "queue",
    ticket_id: "ticket-016",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    demarre_a: new Date().toISOString(),
    ...over,
  };
}

const progres = ev({
  data: {
    index: 2,
    total: 5,
    restants: ["ticket-018", "ticket-019"],
    faits: ["ticket-016"],
  },
});

describe("majDesRuns — l'avancement arrive aussi par événement (ticket-181)", () => {
  it("met à jour l'avancement d'une carte déjà connue", () => {
    // La réservation du run précède son premier queue_progress : un onglet
    // ouvert reçoit un instantané à 0, puis l'avancement en événement.
    const [carte] = majDesRuns([run({ file_total: 0 })], progres, "r1");

    expect(carte?.file_index).toBe(2);
    expect(carte?.file_total).toBe(5);
  });

  it("met à jour les restants et les faits", () => {
    const [carte] = majDesRuns([run()], progres, "r1");

    expect(carte?.file_restants).toEqual(["ticket-018", "ticket-019"]);
    expect(carte?.file_faits).toEqual(["ticket-016"]);
  });

  it("crée un run inconnu en mode file, pas en ticket unique", () => {
    const [carte] = majDesRuns([], progres, "r1");

    expect(carte?.mode).toBe("queue");
    expect(carte?.file_total).toBe(5);
  });

  it("un autre événement ne touche pas à l'avancement", () => {
    const depart = run({ file_index: 2, file_total: 5 });

    const [carte] = majDesRuns([depart], ev({ type: "agent_started" }), "r1");

    expect(carte?.file_index).toBe(2);
    expect(carte?.file_total).toBe(5);
  });

  it("un run unique n'acquiert aucun avancement", () => {
    const [carte] = majDesRuns([], ev({ type: "agent_started" }), "r1");

    expect(carte?.mode).toBe("single");
    expect(carte?.file_total ?? 0).toBe(0);
  });
});

describe("majDesRuns — coût en direct (ticket-197)", () => {
  const base: RunActif = {
    run_id: "r1", project_id: "p", mode: "single", ticket_id: "ticket-001",
    etape: null, agent: null, tour: 0, tokens_entree: 0, tokens_sortie: 0,
    cout_usd: 0, verdict: null, demarre_a: "2026-09-26T08:00:00Z",
  };

  it("cumule le coût des agent_done", () => {
    // Un run créé côté client restait à 0 $ jusqu'au prochain instantané.
    let runs = majDesRuns([base], ev({ type: "agent_done", agent: "codeur", data: { cost_usd: 0.4 } }), "r1");
    runs = majDesRuns(runs, ev({ type: "agent_done", agent: "reviewer", data: { cost_usd: 0.2 } }), "r1");
    expect(runs[0].cout_usd).toBeCloseTo(0.6);
    expect(runs[0].appels).toBe(2);
  });

  it("remet le compteur d'outils à zéro quand un agent démarre", () => {
    let runs = majDesRuns([base], ev({ type: "agent_tool_use", agent: "codeur", data: { tool: "Read" } }), "r1");
    runs = majDesRuns(runs, ev({ type: "agent_tool_use", agent: "codeur", data: { tool: "Read" } }), "r1");
    expect(runs[0].outils).toBe(2);
    runs = majDesRuns(runs, ev({ type: "agent_started", agent: "reviewer", data: {} }), "r1");
    expect(runs[0].outils).toBe(0);
  });
});
