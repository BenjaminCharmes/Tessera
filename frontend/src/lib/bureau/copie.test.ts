import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { DUREE_DE_LA_COPIE_MS, copieVisible, libelleDeLaCopie, retourDeCopie } from "./copie";

const DEPART = "2026-10-27T09:00:00.000Z";
const T0 = Date.parse(DEPART);

function ev(
  type: EventType,
  agent: AgentRole | null = null,
  data: Record<string, unknown> = {},
  timestamp = DEPART,
): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp };
}

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const refusDuReviewer = ev("agent_done", "reviewer", { content: "CHANGES_REQUESTED\n- un test manque" });
const refusDuValidateur = ev("validation_done", null, { verdict: "CHANGES_REQUESTED", approved: false });

describe("retourDeCopie", () => {
  it("is null at the first coder start: nobody has refused anything yet", () => {
    const etat = rejouer([ev("agent_started", "codeur", { round: 1 })]);

    expect(retourDeCopie(etat, T0)).toBeNull();
  });

  it("names the reviewer and the round when the coder restarts after CHANGES_REQUESTED", () => {
    const etat = rejouer([ev("agent_started", "codeur", { round: 1 }), refusDuReviewer, ev("agent_started", "codeur", { round: 2 })]);

    expect(retourDeCopie(etat, T0 + 1_000)).toEqual({ poste: "reviewer", tour: 2 });
  });

  it("names the validator after a refused validation, which comes after the reviewer's", () => {
    const etat = rejouer([
      ev("agent_started", "codeur", { round: 1 }),
      ev("agent_done", "reviewer", { content: "APPROVED" }),
      refusDuValidateur,
      ev("agent_started", "codeur", { round: 2 }),
    ]);

    expect(retourDeCopie(etat, T0)).toEqual({ poste: "validateur", tour: 2 });
  });

  it("ignores an approved review and an approved validation", () => {
    const etat = rejouer([
      ev("agent_started", "codeur", { round: 1 }),
      ev("agent_done", "reviewer", { content: "APPROVED" }),
      ev("validation_done", null, { verdict: "APPROVED", approved: true }),
      ev("agent_started", "codeur", { round: 2 }),
    ]);

    expect(retourDeCopie(etat, T0)).toBeNull();
  });

  it("ignores a refusal that an earlier coder restart already answered", () => {
    const etat = rejouer([
      ev("agent_started", "codeur", { round: 1 }),
      refusDuReviewer,
      ev("agent_started", "codeur", { round: 2 }),
      ev("agent_started", "codeur", { round: 3 }),
    ]);

    expect(retourDeCopie(etat, T0)).toBeNull();
  });

  it("lasts 15 s from the coder's restart, no more, and never before it", () => {
    const etat = rejouer([ev("agent_started", "codeur", { round: 1 }), refusDuReviewer, ev("agent_started", "codeur", { round: 2 })]);

    expect(retourDeCopie(etat, T0 + DUREE_DE_LA_COPIE_MS - 1)).not.toBeNull();
    expect(retourDeCopie(etat, T0 + DUREE_DE_LA_COPIE_MS)).toBeNull();
    expect(retourDeCopie(etat, T0 - 1)).toBeNull();
  });

  it("counts the coder's starts when the event carries no round", () => {
    const etat = rejouer([ev("agent_started", "codeur"), refusDuReviewer, ev("agent_started", "codeur")]);

    expect(retourDeCopie(etat, T0)?.tour).toBe(2);
  });

  it("treats an unreadable timestamp as nothing to draw", () => {
    const etat = rejouer([
      ev("agent_started", "codeur", { round: 1 }),
      refusDuReviewer,
      ev("agent_started", "codeur", { round: 2 }, "not a date"),
    ]);

    expect(retourDeCopie(etat, T0)).toBeNull();
  });
});

describe("copieVisible", () => {
  const retour = { poste: "reviewer", tour: 2 } as const;
  const libre = { faits: ["reviewer"], absents: [], clos: false, fete: false } as const;

  it("keeps the trip when the agent is done, in place, and the room is open", () => {
    expect(copieVisible(retour, libre)).toEqual(retour);
  });

  it("drops it when the agent is elsewhere, still working, or the room is closed or celebrating", () => {
    expect(copieVisible(retour, { ...libre, absents: ["reviewer"] })).toBeNull();
    expect(copieVisible(retour, { ...libre, faits: [] })).toBeNull();
    expect(copieVisible(retour, { ...libre, clos: true })).toBeNull();
    expect(copieVisible(retour, { ...libre, fete: true })).toBeNull();
    expect(copieVisible(null, libre)).toBeNull();
  });
});

describe("libelleDeLaCopie", () => {
  it("writes the round and the agent", () => {
    expect(libelleDeLaCopie({ poste: "reviewer", tour: 2 })).toBe("tour 2 — le reviewer rend sa copie");
    expect(libelleDeLaCopie({ poste: "validateur", tour: 3 })).toBe("tour 3 — le validateur rend sa copie");
  });
});
