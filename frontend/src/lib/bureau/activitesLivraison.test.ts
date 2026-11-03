import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { BOITE_X, libelleActivite, placerLesAgents, postesFaits } from "./activites";
import type { AgentPlace } from "./activites";
import { postesDuRun } from "./postesDuRun";
import { livraisonEnCours } from "./suite";

function evenement(type: EventType, agent: AgentRole | null = null): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data: {}, timestamp: "2026-10-29T10:00:00.000Z" };
}

function rejouer(...evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

/** Le pipeline fini, puis les événements de suite donnés. */
function etatApresPipeline(...suite: OrchestratorEvent[]): StreamState {
  return rejouer(
    evenement("agent_started", "codeur"),
    evenement("agent_done", "codeur"),
    evenement("pipeline_done"),
    ...suite,
  );
}

function placer(etat: StreamState, fete = false): AgentPlace[] {
  const faits = postesFaits(postesDuRun(etat));
  return placerLesAgents(faits, {}, etat.runClosed, fete, null, null, livraisonEnCours(etat));
}

function codeur(agents: AgentPlace[]): AgentPlace | undefined {
  return agents.find((a) => a.poste === "codeur");
}

describe("placerLesAgents during the delivery", () => {
  it("puts the coder at the mailbox between livraison_started and livraison_done", () => {
    const agents = placer(etatApresPipeline(evenement("livraison_started")));

    expect(codeur(agents)).toMatchObject({ activite: "depose", x: BOITE_X, niveau: "fond", parti: false });
    expect(libelleActivite("depose")).toBe("dépose la PR");
  });

  it("puts the coder back to a break activity once the delivery is done", () => {
    const agents = placer(etatApresPipeline(evenement("livraison_started"), evenement("livraison_done")));

    expect(codeur(agents)?.activite).not.toBe("depose");
    expect(codeur(agents)?.x).not.toBe(BOITE_X);
  });

  it("leaves the other agents on their own activity", () => {
    const etat = etatApresPipeline(evenement("livraison_started"));
    const faits = postesFaits(postesDuRun(etat));
    const agents = placerLesAgents(faits, { codeur: "tasse" }, false, false, null, null, true);

    expect(agents.filter((a) => a.activite === "depose")).toHaveLength(1);
  });

  it("draws the coder at the mailbox even before it has finished a round", () => {
    const agents = placerLesAgents([], {}, false, false, null, null, true);

    expect(agents.map((a) => a.poste)).toEqual(["codeur"]);
    expect(agents[0]?.activite).toBe("depose");
  });

  it("never lets the delivery override the party or the door", () => {
    expect(placerLesAgents([], {}, true, false, null, null, true).every((a) => a.parti)).toBe(true);
    expect(placerLesAgents([], {}, false, true, null, null, true).every((a) => a.activite === "fete")).toBe(true);
  });
});
