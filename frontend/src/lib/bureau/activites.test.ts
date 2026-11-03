import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import {
  PLACES_MACHINE,
  PORTE_X,
  TABLEAU_X,
  appliquerPlafond,
  libelleActivite,
  machineEnService,
  quiBavarde,
  placerLesAgents,
  postesFaits,
  renouveler,
  tirerActivite,
} from "./activites";
import type { Activites } from "./activites";
import { posteEnPlan } from "./plan";
import { POSTES, postesDuRun } from "./postesDuRun";
import type { PosteDuRun, PosteId } from "./postesDuRun";

function suite(...valeurs: number[]): () => number {
  let i = 0;
  return () => valeurs[i++ % valeurs.length] ?? 0;
}

function postes(etats: Partial<Record<PosteId, PosteDuRun["etat"]>>): PosteDuRun[] {
  return POSTES.map((poste) => ({ poste, etat: etats[poste] ?? "libre" }));
}

describe("tirerActivite", () => {
  it("can draw each of the three activities", () => {
    expect(tirerActivite(() => 0)).toBe("tasse");
    expect(tirerActivite(() => 0.5)).toBe("pause");
    expect(tirerActivite(() => 0.99)).toBe("machine");
  });

  it("never reads past the table when the draw reaches 1", () => {
    expect(tirerActivite(() => 1)).toBe("machine");
  });
});

describe("libelleActivite", () => {
  it("names the party", () => {
    expect(libelleActivite("fete")).toBe("fête la PR mergée");
  });

  it("says each activity in words", () => {
    expect(libelleActivite("tasse")).toBe("boit un café à son poste");
    expect(libelleActivite("pause")).toBe("fait une pause");
    expect(libelleActivite("machine")).toBe("prend un café à la machine");
  });
});

describe("postesFaits", () => {
  it("keeps only the posts whose agent is done", () => {
    const etats = postes({ codeur: "fait", testeur: "occupe", securite: "libre", reviewer: "fait" });

    expect(postesFaits(etats)).toEqual(["codeur", "reviewer"]);
  });
});

describe("renouveler", () => {
  it("gives no activity to a post that is busy or free", () => {
    const etats = postes({ codeur: "fait", testeur: "occupe" });
    const avant: Activites = { testeur: "machine", securite: "pause" };

    const apres = renouveler(avant, postesFaits(etats), suite(0.99));

    expect(Object.keys(apres)).toEqual(["codeur"]);
  });

  it("draws an activity for an agent that has none yet", () => {
    expect(renouveler({}, ["codeur"], suite(0.5))).toEqual({ codeur: "pause" });
  });

  it("keeps the activity most of the time", () => {
    const apres = renouveler({ codeur: "machine" }, ["codeur"], suite(0.9));

    expect(apres).toEqual({ codeur: "machine" });
  });

  it("changes the activity one time in four", () => {
    const apres = renouveler({ codeur: "machine" }, ["codeur"], suite(0.1, 0));

    expect(apres).toEqual({ codeur: "tasse" });
  });
});

describe("appliquerPlafond", () => {
  it("sends the fourth agent heading to the machine back to his own post", () => {
    const faits: PosteId[] = ["codeur", "testeur", "securite", "reviewer"];
    const brutes: Activites = { codeur: "machine", testeur: "machine", securite: "machine", reviewer: "machine" };

    const effectives = appliquerPlafond(brutes, faits);

    const aLaMachine = faits.filter((p) => effectives[p] === "machine");
    expect(aLaMachine).toHaveLength(PLACES_MACHINE);
    expect(aLaMachine).toEqual(["codeur", "testeur", "securite"]);
    expect(effectives.reviewer).toBe("tasse");
  });

  it("leaves the other activities alone", () => {
    const effectives = appliquerPlafond({ codeur: "pause", testeur: "tasse" }, ["codeur", "testeur"]);

    expect(effectives).toEqual({ codeur: "pause", testeur: "tasse" });
  });
});

describe("placerLesAgents", () => {
  it("places only the done agents while the run is open, each by activity", () => {
    const faits: PosteId[] = ["codeur", "testeur", "securite"];
    const effectives: Activites = { codeur: "machine", testeur: "pause", securite: "tasse" };

    const agents = placerLesAgents(faits, effectives, false);

    expect(agents.map((a) => [a.poste, a.activite, a.niveau])).toEqual([
      ["codeur", "machine", "fond"],
      ["testeur", "pause", "rangee"],
      ["securite", "tasse", "rangee"],
    ]);
    expect(agents.every((a) => !a.parti)).toBe(true);
  });

  it("stands two agents at the machine on different places", () => {
    const agents = placerLesAgents(["codeur", "testeur"], { codeur: "machine", testeur: "machine" }, false);

    expect(new Set(agents.map((a) => a.x + a.decalage)).size).toBe(2);
    expect(quiBavarde(agents)).toBe("codeur");
  });

  it("lets nobody chat when a single agent is at the machine", () => {
    const agents = placerLesAgents(["codeur", "testeur"], { codeur: "machine", testeur: "tasse" }, false);

    expect(quiBavarde(agents)).toBeNull();
  });

  it("puts all five agents at the door, gone, once the run is closed", () => {
    const agents = placerLesAgents(["codeur"], { codeur: "pause" }, true);

    expect(agents).toHaveLength(5);
    for (const agent of agents) {
      expect(agent.parti).toBe(true);
      expect(agent.activite).toBeNull();
      expect(agent.niveau).toBe("fond");
      expect(agent.x).toBe(PORTE_X);
    }
  });

  it("stands all five agents at their posts, arms up, when the PR is merged, even in a closed run", () => {
    const agents = placerLesAgents(["codeur"], { codeur: "machine" }, true, true);

    expect(agents.map((a) => [a.poste, a.activite, a.niveau, a.parti])).toEqual(
      POSTES.map((poste) => [poste, "fete", "rangee", false]),
    );
    expect(new Set(agents.map((a) => a.x)).size).toBe(5);
    expect(machineEnService(agents)).toBe(false);
  });
});

function evenement(
  type: EventType,
  agent: AgentRole | null,
  data: Record<string, unknown> = {},
): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: "2026-01-01T00:00:00.000Z" };
}

/** Ce que la pièce place pour un run rejoué : les faits, puis le poste du plan. */
function placesDuRun(evenements: OrchestratorEvent[]) {
  const etat: StreamState = evenements.reduce(applyEvent, INITIAL);
  const faits = postesFaits(postesDuRun(etat));
  return placerLesAgents(faits, {}, false, false, null, posteEnPlan(etat));
}

describe("placerLesAgents during the plan round", () => {
  const PLAN = { round: 0, phase: "plan" };

  it("stands the post agent at the whiteboard, preparing the plan, between the plan start and done", () => {
    const agents = placesDuRun([evenement("agent_started", "codeur", PLAN)]);

    expect(agents).toHaveLength(1);
    const [agent] = agents;
    expect(agent?.poste).toBe("codeur");
    expect(agent?.activite).toBe("plan");
    expect(libelleActivite("plan")).toBe("prépare le plan");
    expect(agent?.x).toBe(TABLEAU_X);
    expect(agent?.niveau).toBe("fond");
    expect(agent?.parti).toBe(false);
  });

  it("takes the agent back to its post once the plan is done", () => {
    const agents = placesDuRun([
      evenement("agent_started", "codeur", PLAN),
      evenement("agent_done", "codeur", PLAN),
    ]);

    expect(agents).toEqual([]);
  });

  it("leaves no whiteboard walker in a run without a plan", () => {
    const agents = placesDuRun([evenement("agent_started", "codeur", { round: 1 })]);

    expect(agents.filter((a) => a.activite === "plan")).toEqual([]);
  });

  it("never lets a plan override the party or the door", () => {
    expect(placerLesAgents([], {}, true, false, null, "codeur").every((a) => a.parti)).toBe(true);
    expect(placerLesAgents([], {}, false, true, null, "codeur").every((a) => a.activite === "fete")).toBe(true);
  });
});

describe("machineEnService", () => {
  it("is true if and only if an agent is at the machine", () => {
    const sans = placerLesAgents(["codeur"], { codeur: "tasse" }, false);
    const avec = placerLesAgents(["codeur", "testeur"], { codeur: "tasse", testeur: "machine" }, false);

    expect(machineEnService([])).toBe(false);
    expect(machineEnService(sans)).toBe(false);
    expect(machineEnService(avec)).toBe(true);
  });

  it("is false once everybody has left", () => {
    expect(machineEnService(placerLesAgents(["codeur"], { codeur: "machine" }, true))).toBe(false);
  });
});
