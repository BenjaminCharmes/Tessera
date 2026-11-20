import { describe, expect, it } from "vitest";
import { libelleDesAnomalies, posteDuMarqueur } from "./marqueurAnomalie";
import type { Anomalie, RunActif } from "../../types/api";

function anomalie(cle: string): Anomalie {
  return { regle: "silence", cle, ticket_id: "t", message: "m", mesure: 1, seuil: 1, unite: "s" };
}

function run(anomalies?: Anomalie[]): RunActif {
  return {
    run_id: "r", project_id: "p", mode: "single", ticket_id: "t", etape: null, agent: null, tour: 1,
    tokens_entree: 0, tokens_sortie: 0, cout_usd: 0, verdict: null, demarre_a: "2026-11-05T08:00:00Z", anomalies,
  };
}

describe("libelleDesAnomalies", () => {
  it("says one anomaly in the singular and the others in the plural", () => {
    expect(libelleDesAnomalies(1)).toBe("1 anomalie");
    expect(libelleDesAnomalies(3)).toBe("3 anomalies");
  });
});

describe("posteDuMarqueur", () => {
  it("picks the first agent at work, with the count of the run", () => {
    expect(posteDuMarqueur(run([anomalie("a"), anomalie("b")]), false, ["reviewer", "validateur"])).toEqual({
      poste: "reviewer",
      nombre: 2,
    });
  });

  it("picks nobody without an anomaly, without a run, without data, once closed, or without an agent at work", () => {
    expect(posteDuMarqueur(run([]), false, ["codeur"])).toBeNull();
    expect(posteDuMarqueur(run(undefined), false, ["codeur"])).toBeNull();
    expect(posteDuMarqueur(undefined, false, ["codeur"])).toBeNull();
    expect(posteDuMarqueur(run([anomalie("a")]), true, ["codeur"])).toBeNull();
    expect(posteDuMarqueur(run([anomalie("a")]), false, [])).toBeNull();
  });
});
