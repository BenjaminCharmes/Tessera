import { describe, expect, it } from "vitest";
import {
  PLACES_MACHINE,
  PORTE_X,
  appliquerPlafond,
  libelleActivite,
  machineEnService,
  placerLesAgents,
  postesFaits,
  renouveler,
  tirerActivite,
} from "./activites";
import type { Activites } from "./activites";
import { POSTES } from "./postesDuRun";
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
    expect(tirerActivite(() => 0.5)).toBe("etire");
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
    expect(libelleActivite("etire")).toBe("s'étire");
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
    const avant: Activites = { testeur: "machine", securite: "etire" };

    const apres = renouveler(avant, postesFaits(etats), suite(0.99));

    expect(Object.keys(apres)).toEqual(["codeur"]);
  });

  it("draws an activity for an agent that has none yet", () => {
    expect(renouveler({}, ["codeur"], suite(0.5))).toEqual({ codeur: "etire" });
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
    const effectives = appliquerPlafond({ codeur: "etire", testeur: "tasse" }, ["codeur", "testeur"]);

    expect(effectives).toEqual({ codeur: "etire", testeur: "tasse" });
  });
});

describe("placerLesAgents", () => {
  it("places only the done agents while the run is open, each by activity", () => {
    const faits: PosteId[] = ["codeur", "testeur", "securite"];
    const effectives: Activites = { codeur: "machine", testeur: "etire", securite: "tasse" };

    const agents = placerLesAgents(faits, effectives, false);

    expect(agents.map((a) => [a.poste, a.activite, a.niveau])).toEqual([
      ["codeur", "machine", "fond"],
      ["testeur", "etire", "rangee"],
      ["securite", "tasse", "rangee"],
    ]);
    expect(agents.every((a) => !a.parti)).toBe(true);
  });

  it("stands two agents at the machine on different places", () => {
    const agents = placerLesAgents(["codeur", "testeur"], { codeur: "machine", testeur: "machine" }, false);

    expect(new Set(agents.map((a) => a.x)).size).toBe(2);
  });

  it("puts all five agents at the door, gone, once the run is closed", () => {
    const agents = placerLesAgents(["codeur"], { codeur: "etire" }, true);

    expect(agents).toHaveLength(5);
    for (const agent of agents) {
      expect(agent.parti).toBe(true);
      expect(agent.activite).toBeNull();
      expect(agent.niveau).toBe("fond");
      expect(agent.x).toBeGreaterThan(PORTE_X - 10);
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
